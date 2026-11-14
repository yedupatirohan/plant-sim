"""Builds services for each request. Every one depends on get_session,
so tests can swap the database with a single override."""
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.repositories.alarm_repo import AlarmRepository
from app.repositories.plant_repo import PlantRepository
from app.repositories.simulation_repo import SimulationRepository
from app.services.alarm_service import AlarmService
from app.services.balance_service import BalanceService
from app.services.detection_service import DetectionService
from app.services.plant_service import PlantService
from app.services.report_service import DataQualityService, DetectAndRaiseService
from app.services.simulation_service import SimulationService
from app.services.topology_service import TopologyService


def plant_service(session: Session = Depends(get_session)) -> PlantService:
    return PlantService(PlantRepository(session))


def topology_service(session: Session = Depends(get_session)) -> TopologyService:
    return TopologyService(PlantRepository(session))


def balance_service(session: Session = Depends(get_session)) -> BalanceService:
    return BalanceService(PlantRepository(session))


def detection_service(session: Session = Depends(get_session)) -> DetectionService:
    return DetectionService(PlantRepository(session))


def detect_and_raise_service(session: Session = Depends(get_session)) -> DetectAndRaiseService:
    return DetectAndRaiseService(DetectionService(PlantRepository(session)),
                                 AlarmService(AlarmRepository(session)))


def alarm_service(session: Session = Depends(get_session)) -> AlarmService:
    return AlarmService(AlarmRepository(session))


def simulation_service(session: Session = Depends(get_session)) -> SimulationService:
    return SimulationService(PlantRepository(session), SimulationRepository(session))


def quality_service(session: Session = Depends(get_session)) -> DataQualityService:
    repo = PlantRepository(session)
    return DataQualityService(repo, TopologyService(repo), BalanceService(repo))