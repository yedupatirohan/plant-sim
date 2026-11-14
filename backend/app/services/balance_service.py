"""Conservation of flow: inflow - outflow - storage change must be near zero."""
from collections import defaultdict

from app.core.errors import NotFoundError
from app.repositories.plant_repo import PlantRepository

MIN_TOLERANCE = 10.0   # m3/h
REL_TOLERANCE = 0.03   # 3% of inflow
WINDOW = 30            # minutes used to estimate storage change


def tolerance_for(inflow: float) -> float:
    return max(MIN_TOLERANCE, REL_TOLERANCE * abs(inflow))


def check_balance(inflow: float, outflow: float, storage_change: float,
                  tolerance: float | None = None) -> dict:
    """Pure rule. All values in m3/h."""
    tol = tolerance_for(inflow) if tolerance is None else tolerance
    residual = abs(inflow - outflow - storage_change)
    return {"residual_m3h": round(residual, 3), "tolerance_m3h": round(tol, 3),
            "violated": residual > tol}


def merge_windows(flags: list[bool]) -> list[tuple[int, int]]:
    """(start, end_inclusive) of each stretch of True."""
    out, i = [], 0
    while i < len(flags):
        if flags[i]:
            j = i
            while j + 1 < len(flags) and flags[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


class BalanceService:
    def __init__(self, repo: PlantRepository):
        self.repo = repo

    def check_facility(self, facility_id: str) -> dict:
        if self.repo.get_facility(facility_id) is None:
            raise NotFoundError(f"Facility {facility_id} not found")

        sensors = self.repo.list_sensors(facility_id)
        pump_s = [s.sensor_id for s in sensors if s.component_type == "PUMP" and s.measurement == "FLOW"]
        valve_s = [s.sensor_id for s in sensors if s.component_type == "VALVE" and s.measurement == "FLOW"]
        tank_s = {s.component_id: s.sensor_id for s in sensors
                  if s.component_type == "TANK" and s.measurement == "LEVEL"}
        capacity = {t.tank_id: t.capacity_m3 for t in self.repo.list_tanks(facility_id)}

        if not valve_s:
            return {"facility_id": facility_id, "status": "NOT_ASSESSABLE",
                    "note": "no valve flow sensors, so outflow cannot be measured",
                    "windows_checked": 0, "violation_windows": 0, "events": []}

        wanted = pump_s + valve_s + list(tank_s.values())
        by_ts: dict = defaultdict(lambda: defaultdict(float))
        sensor_kind = {}
        for sid in pump_s:
            sensor_kind[sid] = ("in", 1.0)
        for sid in valve_s:
            sensor_kind[sid] = ("out", 1.0)
        for tid, sid in tank_s.items():
            sensor_kind[sid] = ("vol", capacity[tid] / 100.0)
        for row in self.repo.get_telemetry_for_sensors(wanted):
            kind, factor = sensor_kind[row.sensor_id]
            by_ts[row.ts_utc][kind] += row.value * factor

        times = sorted(by_ts)
        windows = []
        for i in range(WINDOW, len(times)):
            now, before = by_ts[times[i]], by_ts[times[i - WINDOW]]
            storage = (now["vol"] - before["vol"]) / (WINDOW / 60.0)
            inflow = by_ts[times[i]]["in"]
            res = check_balance(inflow, now["out"], storage)
            windows.append((times[i], res))

        events = []
        for a, b in merge_windows([r["violated"] for _, r in windows]):
            worst = max(windows[k][1]["residual_m3h"] for k in range(a, b + 1))
            events.append({"start_ts": windows[a][0].isoformat(),
                           "end_ts": windows[b][0].isoformat(),
                           "max_residual_m3h": worst})
        return {"facility_id": facility_id,
                "status": "VIOLATIONS" if events else "OK", "note": None,
                "windows_checked": len(windows),
                "violation_windows": sum(1 for _, r in windows if r["violated"]),
                "events": events}

    def check_all(self) -> list[dict]:
        return [self.check_facility(f.facility_id) for f in self.repo.list_facilities()]