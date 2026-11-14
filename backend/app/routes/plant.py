"""Facilities, components, operating modes and telemetry. Thin: calls the service."""
from datetime import datetime

from fastapi import APIRouter, Depends

from app.routes.deps import plant_service
from app.schemas.plant import ComponentsOut, FacilityOut, ModeOut, TelemetryOut
from app.services.plant_service import PlantService

router = APIRouter(tags=["plant"])


@router.get("/facilities", response_model=list[FacilityOut])
def list_facilities(svc: PlantService = Depends(plant_service)):
    return svc.list_facilities()


@router.get("/facilities/{facility_id}", response_model=FacilityOut)
def get_facility(facility_id: str, svc: PlantService = Depends(plant_service)):
    return svc.get_facility(facility_id)


@router.get("/facilities/{facility_id}/components", response_model=ComponentsOut)
def components(facility_id: str, svc: PlantService = Depends(plant_service)):
    return svc.components(facility_id)


@router.get("/facilities/{facility_id}/modes", response_model=list[ModeOut])
def modes(facility_id: str, svc: PlantService = Depends(plant_service)):
    return svc.modes(facility_id)


@router.get("/telemetry/{sensor_id}", response_model=TelemetryOut)
def telemetry(sensor_id: str, start: datetime | None = None, end: datetime | None = None,
              limit: int = 1000, svc: PlantService = Depends(plant_service)):
    return svc.telemetry(sensor_id, start, end, limit)