"""Simulation runs. A missing mode_id becomes HTTP 422 inside the service."""
from fastapi import APIRouter, Depends

from app.routes.deps import simulation_service
from app.schemas.ops import SimulationIn, SimulationOut
from app.services.simulation_service import SimulationService

router = APIRouter(tags=["simulations"])


@router.post("/simulations", response_model=SimulationOut, status_code=201)
def run_simulation(body: SimulationIn, svc: SimulationService = Depends(simulation_service)):
    return svc.run(body.mode_id, body.pump_speed_pct, body.valve_positions)


@router.get("/simulations", response_model=list[SimulationOut])
def list_simulations(svc: SimulationService = Depends(simulation_service)):
    return svc.list_runs()


@router.get("/simulations/{simulation_id}", response_model=SimulationOut)
def get_simulation(simulation_id: str, svc: SimulationService = Depends(simulation_service)):
    return svc.get(simulation_id)