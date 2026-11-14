"""Generate sensors, operating modes and per-mode valve states from master data."""
from datetime import datetime, timedelta

UNITS = {"FLOW": "m3/h", "PRESSURE": "kPa", "LEVEL": "%"}

MODES = [
    ("NORMAL", 80.0),
    ("LOW_DEMAND", 55.0),
    ("PEAK_DEMAND", 100.0),
]


def _pid(prefix: str, n: int, width: int = 3) -> str:
    return f"{prefix}-{n:0{width}d}"


def generate_sensors(master: dict, target: int = 100) -> list[dict]:
    """Fixed placement rule: tank LEVEL, pump FLOW + PRESSURE, then valve FLOW until target."""
    wanted = []
    for t in master["tanks"]:
        wanted.append(("TANK", t["tank_id"], t["facility_id"], "LEVEL"))
    for p in master["pumps"]:
        wanted.append(("PUMP", p["pump_id"], p["facility_id"], "FLOW"))
        wanted.append(("PUMP", p["pump_id"], p["facility_id"], "PRESSURE"))
    for v in master["valves"]:
        wanted.append(("VALVE", v["valve_id"], v["facility_id"], "FLOW"))

    sensors = []
    for i, (ctype, cid, fid, meas) in enumerate(wanted[:target], start=1):
        sensors.append({
            "sensor_id": _pid("SNS", i), "facility_id": fid,
            "component_type": ctype, "component_id": cid,
            "measurement": meas, "unit": UNITS[meas],
        })
    return sensors


def generate_modes(master: dict, start: datetime) -> list[dict]:
    """Three non-overlapping 8-hour windows per facility."""
    modes, n = [], 0
    for fac in master["facilities"]:
        t = start
        for name, speed in MODES:
            n += 1
            end = t + timedelta(hours=8)
            modes.append({
                "mode_id": _pid("MODE", n), "facility_id": fac["facility_id"],
                "name": name, "pump_speed_pct": speed,
                "effective_from": t.isoformat(), "effective_to": end.isoformat(),
            })
            t = end
    return modes


def generate_mode_valve_states(master: dict, modes: list[dict]) -> list[dict]:
    """One row per (mode, valve in the same facility). Derived from valve default + mode."""
    rows = []
    for m in modes:
        for v in master["valves"]:
            if v["facility_id"] != m["facility_id"]:
                continue
            if m["name"] == "LOW_DEMAND" and v["default_state"] == "THROTTLED":
                state, pos = "CLOSED", 0.0
            elif m["name"] == "PEAK_DEMAND":
                state, pos = "OPEN", 100.0
            else:
                state, pos = v["default_state"], v["default_position_pct"]
            rows.append({"mode_id": m["mode_id"], "valve_id": v["valve_id"],
                         "state": state, "position_pct": pos})
    return rows