"""Alarm list, lifecycle and history. Thin: calls the service."""
from fastapi import APIRouter, Depends

from app.routes.deps import alarm_service
from app.schemas.ops import AlarmChangeIn, AlarmEventOut, AlarmOut
from app.services.alarm_service import AlarmService

router = APIRouter(tags=["alarms"])


@router.get("/alarms", response_model=list[AlarmOut])
def list_alarms(facility_id: str | None = None, state: str | None = None,
                svc: AlarmService = Depends(alarm_service)):
    return svc.list_alarms(facility_id, state)


@router.get("/alarms/{alarm_id}", response_model=AlarmOut)
def get_alarm(alarm_id: str, svc: AlarmService = Depends(alarm_service)):
    return svc.get(alarm_id)


@router.post("/alarms/{alarm_id}/acknowledge", response_model=AlarmOut)
def acknowledge(alarm_id: str, body: AlarmChangeIn | None = None,
                svc: AlarmService = Depends(alarm_service)):
    return svc.acknowledge(alarm_id, body.at if body else None)


@router.post("/alarms/{alarm_id}/clear", response_model=AlarmOut)
def clear(alarm_id: str, body: AlarmChangeIn | None = None,
          svc: AlarmService = Depends(alarm_service)):
    return svc.clear(alarm_id, body.at if body else None)


@router.get("/alarms/{alarm_id}/history", response_model=list[AlarmEventOut])
def history(alarm_id: str, svc: AlarmService = Depends(alarm_service)):
    return svc.history(alarm_id)