import csv
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, make_engine
from app.core.errors import NotFoundError
from app.repositories.plant_repo import PlantRepository
from app.services.loader import load_seed
from app.services.detection_service import (
    DetectionService, analyse_pump, classify_fault, expected_pump_values,
    find_overflow, persisted, runs_where, stuck_runs,
)
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # lets the test import the generator package
SEED_DIR = ROOT / "data" / "seed"
TRUTH_CSV = ROOT / "data" / "ground_truth" / "ground_truth.csv"
N = 300


def make(seed=1):
    rng = np.random.default_rng(seed)
    flow = np.round(100 + rng.normal(0, 1, N), 3)
    pres = np.round(600 + rng.normal(0, 2, N), 3)
    return flow, pres


def run(flow, pres):
    return analyse_pump(flow.tolist(), pres.tolist(), [100.0] * N, [600.0] * N)


# ---------- helper functions ----------
def test_classify_rule_matches_generator_rule():
    from generator.validators import classify_fault as generator_rule
    for f in (True, False):
        for p in (True, False):
            assert classify_fault(f, p) == generator_rule(f, p)


def test_expected_pump_values():
    q, kpa = expected_pump_values(100.0, 50.0, 0.001, 100.0)
    assert q == 100.0
    assert kpa == pytest.approx((50.0 - 0.001 * 100.0 ** 2) * 9.81)


def test_runs_where_needs_minimum_length():
    assert runs_where([False, True, True, True, False, True], 3) == [(1, 4)]


def test_persisted_ignores_short_blips():
    assert persisted([True, True, False, True], 3) == [False, False, False, False]
    assert persisted([True, True, True, False], 3) == [True, True, True, False]


def test_stuck_runs_finds_identical_values():
    assert stuck_runs([1, 2, 5, 5, 5, 5, 3], 4) == [(2, 6)]


def test_overflow_runs():
    assert find_overflow([50, 101, 102, 103, 60]) == [(1, 4)]
    assert find_overflow([50, 101, 60]) == []  # one spike is not enough


# ---------- detection on synthetic data ----------
def test_clean_pump_has_no_events():
    flow, pres = make()
    assert run(flow, pres) == []


def test_leak_detected():
    flow, pres = make()
    flow[100:160] *= 0.75
    pres[100:160] *= 0.85
    ev = run(flow, pres)
    assert [e["alarm_type"] for e in ev] == ["LEAK"]
    assert abs(ev[0]["start"] - 100) <= 2


def test_blockage_detected():
    flow, pres = make()
    flow[100:160] *= 0.60
    pres[100:160] *= 1.20
    assert [e["alarm_type"] for e in run(flow, pres)] == ["BLOCKAGE"]


def test_degradation_detected():
    flow, pres = make()
    ramp = np.linspace(1.0, 0.70, 60)
    flow[100:160] *= ramp
    pres[100:160] *= ramp
    ev = run(flow, pres)
    assert [e["alarm_type"] for e in ev] == ["PUMP_DEGRADATION"]
    assert 100 <= ev[0]["start"] <= 125


def test_stuck_flow_sensor_is_sensor_fault():
    flow, pres = make()
    flow[100:160] = flow[100]
    ev = run(flow, pres)
    assert [e["alarm_type"] for e in ev] == ["SENSOR_FAULT"]
    assert ev[0]["sensors"] == ["FLOW"]


def test_single_moving_sensor_is_sensor_fault_not_process():
    flow, pres = make()
    flow[100:130] *= 0.70
    ev = run(flow, pres)
    assert [e["alarm_type"] for e in ev] == ["SENSOR_FAULT"]


# ---------- detection on the real loaded data, checked against ground truth ----------
@pytest.fixture(scope="module")
def service(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "detect_test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    load_seed(engine, SEED_DIR)
    session = sessionmaker(bind=engine)()
    yield DetectionService(PlantRepository(session))
    session.close()
    engine.dispose()


def _truth():
    with open(TRUTH_CSV, newline="") as f:
        return [r for r in csv.DictReader(f) if r["scenario_id"].startswith("SCN-")]


def test_every_scenario_detected_once_with_right_type(service):
    events = service.detect()
    for t in _truth():
        start = datetime.fromisoformat(t["start_ts"])
        end = datetime.fromisoformat(t["end_ts"])
        match = [e for e in events
                 if e["component_id"] == t["component_id"]
                 and e["alarm_type"] == t["expected_alarm_type"]
                 and datetime.fromisoformat(e["start_ts"]) <= end
                 and datetime.fromisoformat(e["end_ts"]) >= start]
        assert len(match) == 1, (t["scenario_id"], events)


def test_no_false_alarms_outside_ground_truth(service):
    assert len(service.detect()) == len(_truth())


def test_unknown_facility_raises_not_found(service):
    with pytest.raises(NotFoundError):
        service.detect("FAC-999")