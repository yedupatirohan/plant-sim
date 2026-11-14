from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, make_engine
from app.core.errors import NotFoundError
from app.repositories.plant_repo import PlantRepository
from app.services.balance_service import (
    BalanceService, check_balance, merge_windows, tolerance_for,
)
from app.services.loader import load_seed
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def test_edge_case_row_is_violation():
    r = check_balance(500.0, 380.0, 5.0, tolerance=10.0)
    assert r["residual_m3h"] == 115.0
    assert r["violated"] is True


def test_exactly_at_tolerance_is_valid():
    assert check_balance(100.0, 90.0, 0.0, tolerance=10.0)["violated"] is False


def test_balanced_row_is_valid():
    assert check_balance(500.0, 400.0, 100.0)["violated"] is False


def test_tolerance_scales_with_inflow():
    assert tolerance_for(100.0) == 10.0
    assert tolerance_for(2000.0) == pytest.approx(60.0)


def test_merge_windows():
    assert merge_windows([False, True, True, False, True]) == [(1, 2), (4, 4)]


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "balance_test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    load_seed(engine, SEED_DIR)
    session = sessionmaker(bind=engine)()
    yield BalanceService(PlantRepository(session))
    session.close()
    engine.dispose()


def test_healthy_start_has_no_violations(service):
    for r in service.check_all():
        early = [e for e in r["events"] if e["start_ts"] < "2026-01-01T04:00:00"]
        assert early == [], r


def test_report_shape(service):
    r = service.check_facility("FAC-001")
    assert r["windows_checked"] > 900
    assert set(r) == {"facility_id", "status", "note", "windows_checked",
                      "violation_windows", "events"}


def test_unknown_facility_raises_not_found(service):
    with pytest.raises(NotFoundError):
        service.check_facility("FAC-999")


def test_facility_without_valve_sensors_is_not_assessable(service):
    r = service.check_facility("FAC-003")
    assert r["status"] == "NOT_ASSESSABLE"
    assert r["events"] == []