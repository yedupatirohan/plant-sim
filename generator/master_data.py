"""Generate master data and a valid topology. Deterministic for a given seed."""
from datetime import date

import numpy as np

FULL_SCALE = {"facilities": 3, "pumps": 20, "tanks": 30, "valves": 60}


def _pid(prefix: str, n: int, width: int = 3) -> str:
    return f"{prefix}-{n:0{width}d}"


def _split(total: int, parts: int) -> list[int]:
    """Split total into parts as evenly as possible (fixed rule, no randomness)."""
    base, extra = divmod(total, parts)
    return [base + (1 if i < extra else 0) for i in range(parts)]


def generate_master(seed: int, scale: dict | None = None) -> dict:
    scale = scale or FULL_SCALE
    rng = np.random.default_rng(seed)
    n_fac = scale["facilities"]

    pumps_per = _split(scale["pumps"], n_fac)
    tanks_per = _split(scale["tanks"], n_fac)
    valves_per = _split(scale["valves"], n_fac)

    facilities, pumps, tanks, valves, pipes = [], [], [], [], []
    pump_n = tank_n = valve_n = pipe_n = 0

    for f in range(n_fac):
        fid = _pid("FAC", f + 1)
        facilities.append({
            "facility_id": fid,
            "name": f"Plant {chr(65 + f)}",
            "status": "ACTIVE",
            "commissioned_on": date(2015 + f, 1, 1).isoformat(),
        })

        fac_tanks, fac_pumps, fac_valves = [], [], []
        for _ in range(tanks_per[f]):
            tank_n += 1
            cap = float(round(rng.uniform(200, 1000), 1))
            area = float(round(rng.uniform(15, 60), 1))
            t = {
                "tank_id": _pid("TANK", tank_n), "facility_id": fid, "name": f"Tank {tank_n}",
                "capacity_m3": cap, "cross_section_m2": area,
                "min_level_pct": 10.0, "max_level_pct": 95.0, "status": "IN_SERVICE",
            }
            tanks.append(t)
            fac_tanks.append(t["tank_id"])

        for _ in range(pumps_per[f]):
            pump_n += 1
            rated = float(round(rng.uniform(80, 250), 1))
            shutoff = float(round(rng.uniform(40, 80), 1))
            # Head lost at rated flow is 30-50% of shutoff head, so pressure stays positive.
            drop_share = rng.uniform(0.3, 0.5)
            p = {
                "pump_id": _pid("PUMP", pump_n), "facility_id": fid, "name": f"Pump {pump_n}",
                "rated_flow_m3h": rated,
                "shutoff_head_m": shutoff,
                "curve_coeff_k": float(round(shutoff * drop_share / rated ** 2, 8)),
                "status": "RUNNING", "effective_from": "2024-01-01", "effective_to": None,
            }
            pumps.append(p)
            fac_pumps.append(p["pump_id"])

        for _ in range(valves_per[f]):
            valve_n += 1
            state = "OPEN" if valve_n % 5 else "THROTTLED"
            v = {
                "valve_id": _pid("VALVE", valve_n), "facility_id": fid, "name": f"Valve {valve_n}",
                "default_state": state, "default_position_pct": 100.0 if state == "OPEN" else 60.0,
            }
            valves.append(v)
            fac_valves.append(v["valve_id"])

        # Topology: one connected chain per facility.
        # Interleave tanks, valves and pumps in a fixed order, then join neighbours.
        nodes = []
        for i in range(max(len(fac_tanks), len(fac_pumps), len(fac_valves))):
            for group in (fac_tanks, fac_valves, fac_pumps):
                if i < len(group):
                    nodes.append(group[i])
        # leftover valves (valves outnumber the others)
        used = set(nodes)
        nodes += [n for n in fac_valves if n not in used]

        for a, b in zip(nodes, nodes[1:]):
            pipe_n += 1
            pipes.append({
                "pipe_id": _pid("PIPE", pipe_n), "facility_id": fid,
                "from_node_id": a, "to_node_id": b,
                "length_m": float(round(rng.uniform(10, 200), 1)),
                "diameter_mm": float(rng.choice([100, 150, 200, 250])),
            })

    return {"facilities": facilities, "pumps": pumps, "tanks": tanks,
            "valves": valves, "pipes": pipes}