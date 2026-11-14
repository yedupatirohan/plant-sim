"""Database access for simulation runs. No business rules here."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.network import SimulationRun


class SimulationRepository:
    def __init__(self, session: Session):
        self.session = session

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(SimulationRun)) or 0

    def add(self, run: SimulationRun) -> SimulationRun:
        self.session.add(run)
        self.session.commit()
        return run

    def get(self, simulation_id: str) -> SimulationRun | None:
        return self.session.get(SimulationRun, simulation_id)

    def list_runs(self) -> list[SimulationRun]:
        return list(self.session.scalars(
            select(SimulationRun).order_by(SimulationRun.simulation_id)))