from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, make_engine
from app.core.errors import NotFoundError, ValidationFailure
from app.repositories.alarm_repo import AlarmRepository
from app.services.alarm_service import AlarmService, can_move
from app.services.loader import load_seed
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def ev(minute: int, kind: str = "LEAK") -> dict:
    return {"facility_id": "FAC-001", "alarm_type": kind, "sensor_ids": ["SNS-031"],
            "detected_at": f"2026-01-01T10:{minute:02d}:00"}


def t(minute: int) -> datetime:
    return datetime(2026, 1, 1, 11, minute)


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "alarm_test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    load_seed(engine, SEED_DIR)
    session = sessionmaker(bind=engine)()
    yield AlarmService(AlarmRepository(session))
    session.close()
    engine.dispose()


def test_lifecycle_rule():
    assert can_move("RAISED", "ACKNOWLEDGED")
    assert can_move("RAISED", "CLEARED")
    assert can_move("ACKNOWLEDGED", "CLEARED")
    assert not can_move("CLEARED", "ACKNOWLEDGED")
    assert not can_move("ACKNOWLEDGED", "RAISED")


def test_raise_creates_alarm_and_event(service):
    made = service.raise_from_events([ev(1)])
    assert len(made) == 1
    assert made[0]["state"] == "RAISED"
    assert made[0]["alarm_id"].startswith("ALM-")
    hist = service.history(made[0]["alarm_id"])
    assert [h["new_state"] for h in hist] == ["RAISED"]
    assert hist[0]["old_state"] is None


def test_raising_same_event_twice_is_ignored(service):
    first = service.raise_from_events([ev(2)])
    again = service.raise_from_events([ev(2)])
    assert len(first) == 1
    assert again == []


def test_acknowledge_then_clear_records_history(service):
    alarm_id = service.raise_from_events([ev(3)])[0]["alarm_id"]
    assert service.acknowledge(alarm_id, at=t(1))["state"] == "ACKNOWLEDGED"
    cleared = service.clear(alarm_id, at=t(2))
    assert cleared["state"] == "CLEARED"
    assert cleared["cleared_at"] == "2026-01-01T11:02:00"
    hist = service.history(alarm_id)
    assert [(h["old_state"], h["new_state"]) for h in hist] == [
        (None, "RAISED"), ("RAISED", "ACKNOWLEDGED"), ("ACKNOWLEDGED", "CLEARED")]


def test_clear_directly_from_raised(service):
    alarm_id = service.raise_from_events([ev(4)])[0]["alarm_id"]
    assert service.clear(alarm_id, at=t(3))["state"] == "CLEARED"


def test_cannot_change_a_cleared_alarm(service):
    alarm_id = service.raise_from_events([ev(5)])[0]["alarm_id"]
    service.clear(alarm_id, at=t(4))
    with pytest.raises(ValidationFailure):
        service.acknowledge(alarm_id, at=t(5))
    with pytest.raises(ValidationFailure):
        service.clear(alarm_id, at=t(6))


def test_cannot_acknowledge_twice(service):
    alarm_id = service.raise_from_events([ev(6)])[0]["alarm_id"]
    service.acknowledge(alarm_id, at=t(7))
    with pytest.raises(ValidationFailure):
        service.acknowledge(alarm_id, at=t(8))


def test_change_before_raised_time_rejected(service):
    alarm_id = service.raise_from_events([ev(7)])[0]["alarm_id"]
    with pytest.raises(ValidationFailure):
        service.clear(alarm_id, at=datetime(2026, 1, 1, 9, 0))


def test_unknown_alarm_not_found(service):
    with pytest.raises(NotFoundError):
        service.acknowledge("ALM-999999")
    with pytest.raises(NotFoundError):
        service.history("ALM-999999")


def test_list_filters_by_state(service):
    cleared = service.list_alarms(state="CLEARED")
    assert cleared
    assert all(a["state"] == "CLEARED" for a in cleared)
    with pytest.raises(ValidationFailure):
        service.list_alarms(state="BROKEN")