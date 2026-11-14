"""Metrics: scoring rules on small made-up data, plus the real file and endpoint."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_session, make_engine
from app.core.errors import NotFoundError
from app.main import app as fastapi_app
from app.repositories.ground_truth_repo import GroundTruthRepository
from app.services.loader import load_seed
from app.services.metrics_service import score
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def truth(sid, comp, kind, start="2026-01-01T10:00:00", end="2026-01-01T11:00:00"):
    return {"scenario_id": sid, "issue_type": kind, "component_id": comp,
            "sensor_ids": "SNS-001;SNS-002", "start_ts": start, "end_ts": end,
            "expected_alarm_type": kind, "rule_applied": "test"}


def event(comp, kind, start="2026-01-01T10:05:00", end="2026-01-01T10:50:00",
          detected="2026-01-01T10:10:00"):
    return {"facility_id": "FAC-001", "component_type": "PUMP", "component_id": comp,
            "alarm_type": kind, "sensor_ids": ["SNS-001", "SNS-002"],
            "start_ts": start, "end_ts": end, "detected_at": detected}


def edge(sid, issue, comp, kind):
    return {"scenario_id": sid, "issue_type": issue, "component_id": comp, "sensor_ids": "",
            "start_ts": "", "end_ts": "", "expected_alarm_type": kind, "rule_applied": "test"}


def test_perfect_detection_scores_one():
    rows = [truth("A", "PUMP-003", "LEAK"), truth("B", "PUMP-008", "BLOCKAGE")]
    events = [event("PUMP-003", "LEAK"), event("PUMP-008", "BLOCKAGE")]
    r = score(events, rows)
    assert (r["true_positives"], r["false_positives"], r["false_negatives"]) == (2, 0, 0)
    assert (r["precision"], r["recall"], r["f1"]) == (1.0, 1.0, 1.0)


def test_missed_scenario_lowers_recall():
    rows = [truth("A", "PUMP-003", "LEAK"), truth("B", "PUMP-008", "BLOCKAGE")]
    r = score([event("PUMP-003", "LEAK")], rows)
    assert r["false_negatives"] == 1
    assert r["missed"] == ["B"]
    assert r["recall"] == 0.5
    assert r["precision"] == 1.0


def test_false_positive_lowers_precision():
    rows = [truth("A", "PUMP-003", "LEAK")]
    events = [event("PUMP-003", "LEAK"), event("PUMP-005", "LEAK")]
    r = score(events, rows)
    assert r["false_positives"] == 1
    assert r["precision"] == 0.5
    assert r["recall"] == 1.0
    assert r["f1"] == 0.6667


def test_wrong_component_does_not_match():
    r = score([event("PUMP-004", "LEAK")], [truth("A", "PUMP-003", "LEAK")])
    assert (r["true_positives"], r["false_positives"], r["false_negatives"]) == (0, 1, 1)


def test_wrong_type_does_not_match():
    r = score([event("PUMP-003", "BLOCKAGE")], [truth("A", "PUMP-003", "LEAK")])
    assert (r["true_positives"], r["false_positives"], r["false_negatives"]) == (0, 1, 1)


def test_non_overlapping_time_does_not_match():
    late = event("PUMP-003", "LEAK", start="2026-01-01T12:00:00", end="2026-01-01T12:30:00",
                 detected="2026-01-01T12:05:00")
    r = score([late], [truth("A", "PUMP-003", "LEAK")])
    assert (r["true_positives"], r["false_positives"], r["false_negatives"]) == (0, 1, 1)


def test_detection_delay_in_minutes():
    rows = [truth("A", "PUMP-003", "LEAK"), truth("B", "PUMP-008", "BLOCKAGE")]
    events = [event("PUMP-003", "LEAK", detected="2026-01-01T10:10:00"),
              event("PUMP-008", "BLOCKAGE", detected="2026-01-01T10:30:00")]
    r = score(events, rows)
    assert [m["delay_min"] for m in r["matches"]] == [10.0, 30.0]
    assert r["mean_delay_min"] == 20.0
    assert r["max_delay_min"] == 30.0


def test_each_detection_matches_one_truth_only():
    rows = [truth("A", "PUMP-003", "LEAK"), truth("B", "PUMP-003", "LEAK")]
    r = score([event("PUMP-003", "LEAK")], rows)
    assert (r["true_positives"], r["false_negatives"]) == (1, 1)


def test_edge_case_detection_is_not_a_false_positive():
    rows = [edge("EDGE-002", "TANK_LEVEL_EXCEEDS_CAPACITY", "TANK-001", "OVERFLOW")]
    r = score([event("TANK-001", "OVERFLOW")], rows)
    assert r["false_positives"] == 0
    assert r["false_positive_events"] == []
    assert r["edge_cases"][0]["detected"] is True
    assert r["precision"] is None


def test_edge_case_missing_is_reported():
    rows = [edge("EDGE-002", "TANK_LEVEL_EXCEEDS_CAPACITY", "TANK-001", "OVERFLOW")]
    r = score([], rows)
    assert r["edge_cases"][0]["detected"] is False


def test_no_events_and_no_truth_gives_none():
    r = score([], [])
    assert r["true_positives"] == 0
    assert (r["precision"], r["recall"], r["f1"]) == (None, None, None)
    assert r["mean_delay_min"] is None


def test_per_type_counts():
    rows = [truth("A", "PUMP-003", "LEAK"), truth("B", "PUMP-008", "BLOCKAGE")]
    events = [event("PUMP-003", "LEAK"), event("PUMP-011", "PUMP_DEGRADATION")]
    r = score(events, rows)
    assert r["per_type"]["LEAK"] == {"tp": 1, "fp": 0, "fn": 0}
    assert r["per_type"]["BLOCKAGE"] == {"tp": 0, "fp": 0, "fn": 1}
    assert r["per_type"]["PUMP_DEGRADATION"] == {"tp": 0, "fp": 1, "fn": 0}


def test_rows_without_a_detector_type_are_not_scored():
    rows = [edge("EDGE-001", "PIPE_MISSING_NODE", "PIPE-901", "")]
    r = score([], rows)
    assert r["not_scored_here"] == [{"scenario_id": "EDGE-001", "issue_type": "PIPE_MISSING_NODE"}]
    assert r["truth_scenarios"] == 0


def test_repository_reads_real_ground_truth():
    rows = GroundTruthRepository().load()
    assert len(rows) == 13
    assert rows[0]["scenario_id"] == "SCN-001"
    assert rows[0]["start_ts"] != ""


def test_repository_missing_file_is_not_found():
    with pytest.raises(NotFoundError):
        GroundTruthRepository(Path("does-not-exist.csv")).load()


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "metrics_test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    load_seed(engine, SEED_DIR)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    fastapi_app.dependency_overrides[get_session] = override
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
    engine.dispose()


def test_metrics_endpoint_scores_the_eight_timed_scenarios(client):
    response = client.get("/metrics/detection")
    assert response.status_code == 200
    body = response.json()
    assert body["truth_scenarios"] == 8
    assert body["true_positives"] + body["false_negatives"] == 8
    assert body["detections"] >= body["true_positives"]
    assert len(body["edge_cases"]) == 2
    assert len(body["not_scored_here"]) == 3