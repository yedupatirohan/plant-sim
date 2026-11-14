"""Detection metrics. Thin: calls the service."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.repositories.ground_truth_repo import GroundTruthRepository
from app.repositories.plant_repo import PlantRepository
from app.schemas.metrics import MetricsOut
from app.services.detection_service import DetectionService
from app.services.metrics_service import MetricsService

router = APIRouter(tags=["metrics"])


def metrics_service(session: Session = Depends(get_session)) -> MetricsService:
    return MetricsService(DetectionService(PlantRepository(session)), GroundTruthRepository())


@router.get("/metrics/detection", response_model=MetricsOut)
def detection_metrics(svc: MetricsService = Depends(metrics_service)):
    return svc.evaluate()