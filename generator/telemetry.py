"""Generate clean baseline telemetry. Anomalies are injected later, with labels."""
from datetime import datetime, timedelta

import numpy as np

HEAD_TO_KPA = 9.81  # 1 m of water head is about 9.81 kPa
MODE_SPEED = {0: 80.0, 1: 55.0, 2: 100.0}  # NORMAL, LOW_DEMAND, PEAK_DEMAND


def _speed_schedule(steps: int, step_minutes: int = 1) -> np.ndarray:
    """Pump speed follows the operating-mode table: 8-hour shifts
    NORMAL (0-8h), LOW_DEMAND (8-16h), PEAK_DEMAND (16h+). A rule, not random."""
    minutes = np.arange(steps) * step_minutes
    idx = np.minimum(minutes // 480, 2)
    return np.array([MODE_SPEED[int(i)] for i in idx])


def generate_baseline(master: dict, sensors: list[dict], seed: int,
                      steps: int = 1000, start: datetime | None = None,
                      step_minutes: int = 1) -> dict:
    """Return {'timestamps': [...], 'series': {sensor_id: np.ndarray}, 'truth': {...}}."""
    start = start or datetime(2026, 1, 1)
    rng = np.random.default_rng(seed + 1)  # separate stream from master data
    speed = _speed_schedule(steps, step_minutes) / 100.0

    pumps = {p["pump_id"]: p for p in master["pumps"]}
    tanks = {t["tank_id"]: t for t in master["tanks"]}
    valves = {v["valve_id"]: v for v in master["valves"]}

    # Clean physical flow and pressure per pump (before noise)
    pump_flow, pump_pressure = {}, {}
    for pid, p in pumps.items():
        q = p["rated_flow_m3h"] * speed
        head = np.maximum(p["shutoff_head_m"] - p["curve_coeff_k"] * q ** 2, 0.0)
        pump_flow[pid] = q
        pump_pressure[pid] = head * HEAD_TO_KPA

    # Facility totals, used for tank balance and valve flow
    fac_flow: dict[str, np.ndarray] = {}
    for pid, p in pumps.items():
        fac_flow[p["facility_id"]] = fac_flow.get(p["facility_id"], 0) + pump_flow[pid]
    fac_tanks: dict[str, list] = {}
    for tid, t in tanks.items():
        fac_tanks.setdefault(t["facility_id"], []).append(tid)

    # Tank level: integrate net flow. Inflow is the tank's share of pump flow,
    # outflow is a demand that follows the demand cycle.
    dt_h = step_minutes / 60.0
    tank_level = {}
    for tid, t in tanks.items():
        n = len(fac_tanks[t["facility_id"]])
        inflow = fac_flow.get(t["facility_id"], np.zeros(steps)) / n * 0.5
        demand = (0.5 + 0.5 * (1 - speed)) * inflow  # lower pump speed, relatively more draw
        net_m3 = (inflow - demand) * dt_h
        level_m3 = 0.5 * t["capacity_m3"] + np.cumsum(net_m3) - net_m3[0]
        pct = np.clip(level_m3 / t["capacity_m3"] * 100.0,
                      t["min_level_pct"], t["max_level_pct"])
        tank_level[tid] = pct

    # Valve flow: facility flow share scaled by valve position (state at the mode level)
    nvalves = {}
    for v in valves.values():
        nvalves[v["facility_id"]] = nvalves.get(v["facility_id"], 0) + 1

    series = {}
    for s in sensors:
        cid, meas = s["component_id"], s["measurement"]
        if s["component_type"] == "PUMP" and meas == "FLOW":
            clean = pump_flow[cid]
            noise = rng.normal(0, 0.01 * pumps[cid]["rated_flow_m3h"], steps)
        elif s["component_type"] == "PUMP" and meas == "PRESSURE":
            clean = pump_pressure[cid]
            noise = rng.normal(0, 2.0, steps)
        elif s["component_type"] == "TANK" and meas == "LEVEL":
            clean = tank_level[cid]
            noise = rng.normal(0, 0.1, steps)
        else:  # valve flow
            v = valves[cid]
            share = fac_flow.get(v["facility_id"], np.zeros(steps)) / nvalves[v["facility_id"]]
            clean = share * v["default_position_pct"] / 100.0
            noise = rng.normal(0, 0.5, steps)
        series[s["sensor_id"]] = np.round(clean + noise, 3)

    timestamps = [start + timedelta(minutes=step_minutes * i) for i in range(steps)]
    return {"timestamps": timestamps, "series": series, "clean_flow_by_facility": fac_flow}