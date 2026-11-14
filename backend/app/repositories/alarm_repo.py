"""Database access for alarms and alarm events. No business rules here."""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.network import Alarm, AlarmEvent


class AlarmRepository:
    def __init__(self, session: Session):
        self.session = session

    def count(self) -> int:
        return self.session.scalar(select(func.count()).select_from(Alarm)) or 0

    def add(self, alarm: Alarm) -> Alarm:
        self.session.add(alarm)
        self.session.flush()
        return alarm

    def add_event(self, event: AlarmEvent) -> None:
        self.session.add(event)
        self.session.flush()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def get(self, alarm_id: str) -> Alarm | None:
        return self.session.get(Alarm, alarm_id)

    def find_existing(self, facility_id: str, sensor_id: str | None,
                      alarm_type: str, raised_at: datetime) -> Alarm | None:
        stmt = select(Alarm).where(
            Alarm.facility_id == facility_id, Alarm.sensor_id == sensor_id,
            Alarm.alarm_type == alarm_type, Alarm.raised_at == raised_at)
        return self.session.scalars(stmt).first()

    def list_alarms(self, facility_id: str | None = None,
                    state: str | None = None) -> list[Alarm]:
        stmt = select(Alarm).order_by(Alarm.raised_at, Alarm.alarm_id)
        if facility_id:
            stmt = stmt.where(Alarm.facility_id == facility_id)
        if state:
            stmt = stmt.where(Alarm.state == state)
        return list(self.session.scalars(stmt))

    def list_events(self, alarm_id: str) -> list[AlarmEvent]:
        stmt = (select(AlarmEvent).where(AlarmEvent.alarm_id == alarm_id)
                .order_by(AlarmEvent.event_id))
        return list(self.session.scalars(stmt))