"""Rule-based detection of abnormal operating conditions (business logic)."""
from collections import defaultdict
from datetime import datetime

from app.core.errors import NotFoundError
from app.repositories.plant_repo import PlantRepository

HEAD_TO_KPA = 9.81        # 1 m of water head = 9.81 kPa
FLOW_TOL = 0.06           # flow may differ 6% from expected
PRESSURE_TOL = 0.06       # pressure may differ 6% from expected
MIN_RUN = 5               # readings in a row before we trust a deviation
STUCK_RUN = 8             # identical readings in a row = stuck sensor
MERGE_GAP = 10            # join deviation runs separated by a short gap
DEGRADATION_SLOPE = -0.08 # flow ratio falling this much over the event
OVERFLOW_PCT = 100.0      # tank level above 100% is physically impossible


def classify_fault(flow_deviates: bool, pressure_deviates: bool) -> str:
    """Both related sensors move = PROCESS fault; only one = SENSOR fault."""
    if flow_deviates and pressure_deviates:
        return "PROCESS_FAULT"
    if flow_deviates or pressure_deviates:
        return "SENSOR_FAULT"
    return "NORMAL"


def expected_pump_values(rated_flow: float, shutoff_head: float, k: float, speed_pct: float):
    """Healthy pump: flow from speed, pressure from the pump curve."""
    q = rated_flow * speed_pct / 100.0
    head = max(shutoff_head - k * q * q, 0.0)
    return q, head * HEAD_TO_KPA


def runs_where(flags: list[bool], min_run: int) -> list[tuple[int, int]]:
    """(start, end_exclusive) of every stretch of True at least min_run long."""
    runs, i, n = [], 0, len(flags)
    while i < n:
        if flags[i]:
            j = i
            while j < n and flags[j]:
                j += 1
            if j - i >= min_run:
                runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def persisted(flags: list[bool], min_run: int) -> list[bool]:
    out = [False] * len(flags)
    for a, b in runs_where(flags, min_run):
        for k in range(a, b):
            out[k] = True
    return out


def fill_gaps(flags: list[bool], max_gap: int) -> list[bool]:
    out, last = list(flags), None
    for i, f in enumerate(flags):
        if f:
            if last is not None and 0 < i - last - 1 <= max_gap:
                for k in range(last + 1, i):
                    out[k] = True
            last = i
    return out


def stuck_runs(values: list[float], min_run: int) -> list[tuple[int, int]]:
    runs, i, n = [], 0, len(values)
    while i < n:
        j = i + 1
        while j < n and values[j] == values[i]:
            j += 1
        if j - i >= min_run:
            runs.append((i, j))
        i = j
    return runs


def find_overflow(levels: list[float], limit: float = OVERFLOW_PCT, min_run: int = 3):
    return runs_where([v > limit for v in levels], min_run)


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _event(alarm_type, a, b_inclusive, sensors, detect_idx):
    return {"alarm_type": alarm_type, "start": a, "end": b_inclusive,
            "sensors": sensors, "detect": detect_idx}


def analyse_pump(flow, pressure, exp_flow, exp_pressure) -> list[dict]:
    """Pure function. Inputs are equal-length lists. Returns events by index."""
    f_ratio = [f / e if e else 1.0 for f, e in zip(flow, exp_flow)]
    p_ratio = [p / e if e else 1.0 for p, e in zip(pressure, exp_pressure)]
    f_per = persisted([abs(r - 1) > FLOW_TOL for r in f_ratio], MIN_RUN)
    p_per = persisted([abs(r - 1) > PRESSURE_TOL for r in p_ratio], MIN_RUN)
    events: list[dict] = []

    # 1) Stuck sensors: identical values while the partner sensor is normal.
    for name, values, own, partner in (("FLOW", flow, f_per, p_per),
                                       ("PRESSURE", pressure, p_per, f_per)):
        for a, b in stuck_runs(values, STUCK_RUN):
            if classify_fault(True, any(partner[a:b])) == "SENSOR_FAULT":
                events.append(_event("SENSOR_FAULT", a, b - 1, [name], a + STUCK_RUN - 1))
                for k in range(a, b):
                    own[k] = False  # a stuck value is not a process deviation

    # 2) Deviation runs. Join runs of both sensors, then decide what they are.
    union = fill_gaps([f or p for f, p in zip(f_per, p_per)], MERGE_GAP)
    for a, b in runs_where(union, 1):
        both = sum(1 for i in range(a, b) if f_per[i] and p_per[i])
        detect = min(a + MIN_RUN - 1, b - 1)
        if both >= MIN_RUN:  # classify_fault(True, True) = PROCESS_FAULT
            if _mean(p_ratio[a:b]) > 1.0:
                kind = "BLOCKAGE"
            else:
                slope = _mean(f_ratio[max(a, b - 5):b]) - _mean(f_ratio[a:a + 5])
                kind = "PUMP_DEGRADATION" if slope < DEGRADATION_SLOPE else "LEAK"
            events.append(_event(kind, a, b - 1, ["FLOW", "PRESSURE"], detect))
        else:  # only one sensor moved: classify_fault(True, False) = SENSOR_FAULT
            f_cnt = sum(f_per[a:b])
            p_cnt = sum(p_per[a:b])
            sensor = "FLOW" if f_cnt >= p_cnt else "PRESSURE"
            events.append(_event("SENSOR_FAULT", a, b - 1, [sensor], detect))

    return sorted(events, key=lambda e: e["start"])


def _mode_speed(modes: list, ts: datetime) -> float:
    """Pump speed (%) of the latest operating mode that started at or before ts."""
    if not modes:
        return 100.0
    chosen = modes[0]
    for m in modes:
        if m.effective_from <= ts:
            chosen = m
        else:
            break
    return chosen.pump_speed_pct


class DetectionService:
    def __init__(self, repo: PlantRepository):
        self.repo = repo

    def detect(self, facility_id: str | None = None) -> list[dict]:
        if facility_id is not None and self.repo.get_facility(facility_id) is None:
            raise NotFoundError(f"Facility {facility_id} not found")

        pump_sensor, tank_sensors = {}, []
        for s in self.repo.list_sensors(facility_id):
            if s.component_type == "PUMP":
                pump_sensor[(s.component_id, s.measurement)] = s
            elif s.component_type == "TANK" and s.measurement == "LEVEL":
                tank_sensors.append(s)

        modes = defaultdict(list)
        for m in self.repo.list_modes(facility_id):
            modes[m.facility_id].append(m)
        for lst in modes.values():
            lst.sort(key=lambda m: m.effective_from)

        wanted = [s.sensor_id for s in pump_sensor.values()] + [s.sensor_id for s in tank_sensors]
        by_sensor: dict[str, dict] = defaultdict(dict)
        for row in self.repo.get_telemetry_for_sensors(wanted):
            by_sensor[row.sensor_id][row.ts_utc] = row.value

        found: list[dict] = []

        for pump in self.repo.list_pumps(facility_id):
            fs = pump_sensor.get((pump.pump_id, "FLOW"))
            ps = pump_sensor.get((pump.pump_id, "PRESSURE"))
            if fs is None or ps is None:
                continue
            common = sorted(set(by_sensor[fs.sensor_id]) & set(by_sensor[ps.sensor_id]))
            if not common:
                continue
            flow = [by_sensor[fs.sensor_id][t] for t in common]
            pres = [by_sensor[ps.sensor_id][t] for t in common]
            exp = [expected_pump_values(pump.rated_flow_m3h, pump.shutoff_head_m,
                                        pump.curve_coeff_k,
                                        _mode_speed(modes[pump.facility_id], t)) for t in common]
            ids = {"FLOW": fs.sensor_id, "PRESSURE": ps.sensor_id}
            for e in analyse_pump(flow, pres, [x[0] for x in exp], [x[1] for x in exp]):
                found.append({
                    "facility_id": pump.facility_id,
                    "component_type": "PUMP",
                    "component_id": pump.pump_id,
                    "alarm_type": e["alarm_type"],
                    "sensor_ids": [ids[n] for n in e["sensors"]],
                    "start_ts": common[e["start"]].isoformat(),
                    "end_ts": common[e["end"]].isoformat(),
                    "detected_at": common[e["detect"]].isoformat(),
                })

        for s in tank_sensors:
            series = sorted(by_sensor[s.sensor_id].items())
            levels = [v for _, v in series]
            for a, b in find_overflow(levels):
                found.append({
                    "facility_id": s.facility_id,
                    "component_type": "TANK",
                    "component_id": s.component_id,
                    "alarm_type": "OVERFLOW",
                    "sensor_ids": [s.sensor_id],
                    "start_ts": series[a][0].isoformat(),
                    "end_ts": series[b - 1][0].isoformat(),
                    "detected_at": series[min(a + 2, b - 1)][0].isoformat(),
                })

        return sorted(found, key=lambda e: (e["start_ts"], e["component_id"]))