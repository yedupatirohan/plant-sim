"""Steady-state what-if simulation (business logic)."""
import json

from app.core.config import settings
from app.core.errors import NotFoundError, ValidationFailure
from app.models.network import SimulationRun
from app.repositories.plant_repo import PlantRepository
from app.repositories.simulation_repo import SimulationRepository

HEAD_TO_KPA = 9.81
INITIAL_TANK_LEVEL_PCT = 50.0


def steady_state(pumps: list[dict], valve_positions: dict[str, float],
                 tanks: list[dict], speed_pct: float) -> dict:
    """Pure function. Same inputs always give the same output."""
    pump_rows, inflow, warnings = [], 0.0, []
    for p in sorted(pumps, key=lambda x: x["pump_id"]):
        q = p["rated_flow_m3h"] * speed_pct / 100.0
        head = max(p["shutoff_head_m"] - p["curve_coeff_k"] * q * q, 0.0)
        if head == 0.0 and q > 0:
            warnings.append(f"PUMP_NO_HEAD:{p['pump_id']}")
        inflow += q
        pump_rows.append({"pump_id": p["pump_id"], "flow_m3h": round(q, 3),
                          "head_m": round(head, 3),
                          "pressure_kpa": round(head * HEAD_TO_KPA, 3)})

    n = len(valve_positions)
    open_fraction = (sum(valve_positions.values()) / n / 100.0) if n else 0.0
    outflow = inflow * open_fraction
    storage = inflow - outflow
    if inflow > 0 and open_fraction == 0:
        warnings.append("ALL_VALVES_CLOSED")

    headroom = sum(t["capacity_m3"] * (t["max_level_pct"] - INITIAL_TANK_LEVEL_PCT) / 100.0
                   for t in tanks)
    hours_to_full = round(headroom / storage, 3) if storage > 0.01 else None
    return {
        "pumps": pump_rows,
        "inflow_m3h": round(inflow, 3),
        "outflow_m3h": round(outflow, 3),
        "storage_change_m3h": round(storage, 3),
        "open_fraction": round(open_fraction, 4),
        "hours_until_tanks_full": hours_to_full,
        "warnings": warnings,
    }


class SimulationService:
    def __init__(self, plant: PlantRepository, sims: SimulationRepository):
        self.plant = plant
        self.sims = sims

    def run(self, mode_id: str | None, pump_speed_pct: float | None = None,
            valve_positions: dict[str, float] | None = None) -> dict:
        if not mode_id:
            raise ValidationFailure("mode_id is required: a simulation needs an input configuration")
        mode = self.plant.get_mode(mode_id)
        if mode is None:
            raise NotFoundError(f"Operating mode {mode_id} not found")

        speed = mode.pump_speed_pct if pump_speed_pct is None else float(pump_speed_pct)
        if not 0.0 <= speed <= 100.0:
            raise ValidationFailure("pump_speed_pct must be between 0 and 100")

        positions = {s.valve_id: s.position_pct for s in self.plant.get_mode_valve_states(mode_id)}
        for valve_id, pos in (valve_positions or {}).items():
            if valve_id not in positions:
                raise ValidationFailure(f"Valve {valve_id} does not belong to the facility of {mode_id}")
            if not 0.0 <= float(pos) <= 100.0:
                raise ValidationFailure(f"Position for {valve_id} must be between 0 and 100")
            positions[valve_id] = float(pos)

        pumps = [{"pump_id": p.pump_id, "rated_flow_m3h": p.rated_flow_m3h,
                  "shutoff_head_m": p.shutoff_head_m, "curve_coeff_k": p.curve_coeff_k}
                 for p in self.plant.list_pumps(mode.facility_id) if p.status == "RUNNING"]
        tanks = [{"capacity_m3": t.capacity_m3, "max_level_pct": t.max_level_pct}
                 for t in self.plant.list_tanks(mode.facility_id)]

        result = steady_state(pumps, positions, tanks, speed)
        result["facility_id"] = mode.facility_id
        assumptions = {
            "mode_id": mode_id,
            "pump_speed_pct": speed,
            "valve_positions": dict(sorted(positions.items())),
            "initial_tank_level_pct": INITIAL_TANK_LEVEL_PCT,
            "head_to_kpa": HEAD_TO_KPA,
            "pump_curve": "head = shutoff - k * flow^2",
            "outflow_rule": "outflow = inflow * average valve position / 100",
            "deterministic": True,
        }

        sim_id = f"SIM-2026-{self.sims.count() + 1:06d}"
        run = SimulationRun(
            simulation_id=sim_id, mode_id=mode_id, seed=settings.seed,
            assumptions_json=json.dumps(assumptions, sort_keys=True),
            result_json=json.dumps(result, sort_keys=True),
            status="COMPLETED",
        )
        self.sims.add(run)
        return {"simulation_id": sim_id, "mode_id": mode_id, "seed": settings.seed,
                "status": "COMPLETED", "assumptions": assumptions, "result": result}

    def get(self, simulation_id: str) -> dict:
        run = self.sims.get(simulation_id)
        if run is None:
            raise NotFoundError(f"Simulation {simulation_id} not found")
        return {"simulation_id": run.simulation_id, "mode_id": run.mode_id, "seed": run.seed,
                "status": run.status, "assumptions": json.loads(run.assumptions_json),
                "result": json.loads(run.result_json)}

    def list_runs(self) -> list[dict]:
        return [self.get(r.simulation_id) for r in self.sims.list_runs()]