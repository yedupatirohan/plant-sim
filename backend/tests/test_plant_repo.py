"""Tests for PlantRepository using a fresh temporary database."""
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, make_engine
from app.repositories.plant_repo import PlantRepository
from app.services.loader import load_seed
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "repo_test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    load_seed(engine, SEED_DIR)
    session = sessionmaker(bind=engine)()
    yield PlantRepository(session)
    session.close()
    engine.dispose()


def test_lists_all_facilities(repo):
    assert len(repo.list_facilities()) == 3


def test_get_facility_found_and_missing(repo):
    assert repo.get_facility("FAC-001").facility_id == "FAC-001"
    assert repo.get_facility("FAC-999") is None


def test_component_counts(repo):
    assert len(repo.list_pumps()) == 20
    assert len(repo.list_tanks()) == 30
    assert len(repo.list_valves()) == 60
    assert len(repo.list_sensors()) == 100


def test_facility_filter_only_returns_that_facility(repo):
    pumps = repo.list_pumps("FAC-001")
    assert pumps
    assert all(p.facility_id == "FAC-001" for p in pumps)
    assert len(repo.list_pumps("FAC-999")) == 0


def test_modes_and_valve_states(repo):
    modes = repo.list_modes()
    assert len(modes) == 9
    states = repo.get_mode_valve_states(modes[0].mode_id)
    assert states
    assert all(s.mode_id == modes[0].mode_id for s in states)
    assert repo.get_mode("MODE-NOPE") is None


def test_telemetry_is_ordered_and_limited(repo):
    rows = repo.get_telemetry("SNS-001", limit=10)
    assert len(rows) == 10
    times = [r.ts_utc for r in rows]
    assert times == sorted(times)


def test_telemetry_time_filter(repo):
    start = datetime(2026, 1, 1, 0, 10)
    end = datetime(2026, 1, 1, 0, 14)
    rows = repo.get_telemetry("SNS-001", start=start, end=end)
    assert len(rows) == 5
    assert rows[0].ts_utc == start and rows[-1].ts_utc == end


def test_telemetry_for_unknown_sensor_is_empty(repo):
    assert repo.get_telemetry("SNS-999") == []
    assert repo.get_telemetry_for_sensors([]) == []


def test_telemetry_time_range(repo):
    low, high = repo.telemetry_time_range()
    assert low == datetime(2026, 1, 1, 0, 0)
    assert high == datetime(2026, 1, 1, 16, 39)