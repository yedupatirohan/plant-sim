"""Topology, flow balance, detection and data quality. Thin: calls the service."""
from fastapi import APIRouter, Depends

from app.routes.deps import (balance_service, detect_and_raise_service,
                             detection_service, quality_service, topology_service)
from app.schemas.ops import (BalanceOut, DataQualityOut, DetectionEventOut,
                             DetectRunOut, TopologyOut)
from app.services.balance_service import BalanceService
from app.services.detection_service import DetectionService
from app.services.report_service import DataQualityService, DetectAndRaiseService
from app.services.topology_service import TopologyService

router = APIRouter(tags=["analysis"])


@router.get("/topology", response_model=list[TopologyOut])
def topology_all(svc: TopologyService = Depends(topology_service)):
    return svc.check_all()


@router.get("/topology/{facility_id}", response_model=TopologyOut)
def topology_one(facility_id: str, svc: TopologyService = Depends(topology_service)):
    return svc.check_facility(facility_id)


@router.get("/balance", response_model=list[BalanceOut])
def balance_all(svc: BalanceService = Depends(balance_service)):
    return svc.check_all()


@router.get("/balance/{facility_id}", response_model=BalanceOut)
def balance_one(facility_id: str, svc: BalanceService = Depends(balance_service)):
    return svc.check_facility(facility_id)


@router.get("/detection", response_model=list[DetectionEventOut])
def detection_preview(facility_id: str | None = None,
                      svc: DetectionService = Depends(detection_service)):
    """Read-only: shows what detection finds. Raises no alarms."""
    return svc.detect(facility_id)


@router.post("/detection/run", response_model=DetectRunOut)
def detection_run(facility_id: str | None = None,
                  svc: DetectAndRaiseService = Depends(detect_and_raise_service)):
    return svc.run(facility_id)


@router.get("/data-quality", response_model=DataQualityOut)
def data_quality(svc: DataQualityService = Depends(quality_service)):
    return svc.report()