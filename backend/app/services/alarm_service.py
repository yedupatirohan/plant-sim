"""Alarm lifecycle rules (business logic)."""
from datetime import datetime

from app.core.errors import NotFoundError, ValidationFailure
from app.models.network import Alarm, AlarmEvent
from app.repositories.alarm_repo import AlarmRepository

ALLOWED = {
    "RAISED": {"ACKNOWLEDGED", "CLEARED"},
    "ACKNOWLEDGED": {"CLEARED"},
    "CLEARED": set(),
}


def can_move(old_state: str, new_state: str) -> bool:
    """Pure rule for the alarm lifecycle."""
    return new_state in ALLOWED.get(old_state, set())


def _view(a: Alarm) -> dict:
    return {
        "alarm_id": a.alarm_id, "facility_id": a.facility_id, "sensor_id": a.sensor_id,
        "alarm_type": a.alarm_type, "state": a.state,
        "raised_at": a.raised_at.isoformat(),
        "cleared_at": a.cleared_at.isoformat() if a.cleared_at else None,
    }


class AlarmService:
    def __init__(self, repo: AlarmRepository):
        self.repo = repo

    def raise_from_events(self, events: list[dict]) -> list[dict]:
        """Create one RAISED alarm per detection event. Repeats are skipped."""
        created = []
        try:
            for e in events:
                sensor_id = e["sensor_ids"][0] if e.get("sensor_ids") else None
                raised_at = datetime.fromisoformat(e["detected_at"])
                if self.repo.find_existing(e["facility_id"], sensor_id,
                                           e["alarm_type"], raised_at):
                    continue
                alarm = Alarm(
                    alarm_id=f"ALM-{self.repo.count() + 1:06d}",
                    facility_id=e["facility_id"], sensor_id=sensor_id,
                    alarm_type=e["alarm_type"], raised_at=raised_at,
                    cleared_at=None, state="RAISED")
                self.repo.add(alarm)
                self.repo.add_event(AlarmEvent(
                    alarm_id=alarm.alarm_id, old_state=None,
                    new_state="RAISED", changed_at=raised_at))
                created.append(_view(alarm))
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise
        return created

    def _move(self, alarm_id: str, new_state: str, at: datetime | None) -> dict:
        alarm = self.repo.get(alarm_id)
        if alarm is None:
            raise NotFoundError(f"Alarm {alarm_id} not found")
        if not can_move(alarm.state, new_state):
            raise ValidationFailure(
                f"Alarm {alarm_id} cannot go from {alarm.state} to {new_state}")
        when = at or datetime.now().replace(microsecond=0)
        if when <= alarm.raised_at:
            raise ValidationFailure("Time of change must be after the alarm was raised")
        old = alarm.state
        try:
            alarm.state = new_state
            if new_state == "CLEARED":
                alarm.cleared_at = when
            self.repo.add_event(AlarmEvent(
                alarm_id=alarm_id, old_state=old, new_state=new_state, changed_at=when))
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise
        return _view(alarm)

    def acknowledge(self, alarm_id: str, at: datetime | None = None) -> dict:
        return self._move(alarm_id, "ACKNOWLEDGED", at)

    def clear(self, alarm_id: str, at: datetime | None = None) -> dict:
        return self._move(alarm_id, "CLEARED", at)

    def get(self, alarm_id: str) -> dict:
        alarm = self.repo.get(alarm_id)
        if alarm is None:
            raise NotFoundError(f"Alarm {alarm_id} not found")
        return _view(alarm)

    def list_alarms(self, facility_id: str | None = None, state: str | None = None) -> list[dict]:
        if state is not None and state not in ALLOWED:
            raise ValidationFailure(f"Unknown alarm state {state}")
        return [_view(a) for a in self.repo.list_alarms(facility_id, state)]

    def history(self, alarm_id: str) -> list[dict]:
        if self.repo.get(alarm_id) is None:
            raise NotFoundError(f"Alarm {alarm_id} not found")
        return [{"old_state": e.old_state, "new_state": e.new_state,
                 "changed_at": e.changed_at.isoformat()}
                for e in self.repo.list_events(alarm_id)]