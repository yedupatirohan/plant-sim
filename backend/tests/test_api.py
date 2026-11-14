"""API tests: every route group, the one error format, and one end-to-end flow."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_session, make_engine
from app.main import app as fastapi_app
from app.services.loader import load_seed
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "api_test.db"
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


def assert_error(response, status: int, code: str):
    """Every error must use the one standard format."""
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "details"}
    assert body["error"]["code"] == code


def first_mode_id(client) -> str:
    return client.get("/facilities/FAC-001/modes").json()[0]["mode_id"]


# ---------- facilities, components, modes ----------
def test_list_facilities_returns_three(client):
    response = client.get("/facilities")
    assert response.status_code == 200
    assert [f["facility_id"] for f in response.json()] == ["FAC-001", "FAC-002", "FAC-003"]


def test_get_facility(client):
    response = client.get("/facilities/FAC-001")
    assert response.status_code == 200
    assert response.json()["facility_id"] == "FAC-001"


def test_unknown_facility_is_404(client):
    assert_error(client.get("/facilities/FAC-999"), 404, "NOT_FOUND")


def test_components_add_up_to_the_required_volume(client):
    totals = {"pumps": 0, "tanks": 0, "valves": 0}
    for fid in ("FAC-001", "FAC-002", "FAC-003"):
        data = client.get(f"/facilities/{fid}/components").json()
        for name in totals:
            totals[name] += len(data[name])
    assert totals == {"pumps": 20, "tanks": 30, "valves": 60}


def test_components_unknown_facility_is_404(client):
    assert_error(client.get("/facilities/FAC-999/components"), 404, "NOT_FOUND")


def test_modes_have_speed_in_percent(client):
    modes = client.get("/facilities/FAC-001/modes").json()
    assert len(modes) > 0
    assert all(0 <= m["pump_speed_pct"] <= 100 for m in modes)


# ---------- telemetry ----------
def test_telemetry_returns_points_with_unit(client):
    sensor = client.get("/facilities/FAC-001/components").json()["sensors"][0]
    response = client.get(f"/telemetry/{sensor['sensor_id']}", params={"limit": 5})
    body = response.json()
    assert response.status_code == 200
    assert body["count"] == 5 and len(body["points"]) == 5
    assert body["unit"] == sensor["unit"]


def test_telemetry_unknown_sensor_is_404(client):
    assert_error(client.get("/telemetry/SNS-999"), 404, "NOT_FOUND")


def test_telemetry_bad_limit_is_422(client):
    assert_error(client.get("/telemetry/SNS-031", params={"limit": 0}), 422, "VALIDATION_FAILED")


def test_telemetry_start_after_end_is_422(client):
    params = {"start": "2026-01-02T00:00:00", "end": "2026-01-01T00:00:00"}
    assert_error(client.get("/telemetry/SNS-031", params=params), 422, "VALIDATION_FAILED")


# ---------- topology, balance, detection, data quality ----------
def test_topology_covers_all_facilities(client):
    data = client.get("/topology").json()
    assert len(data) == 3
    assert all(item["status"] in {"OK", "ISSUES"} for item in data)


def test_topology_unknown_facility_is_404(client):
    assert_error(client.get("/topology/FAC-999"), 404, "NOT_FOUND")


def test_balance_covers_all_facilities(client):
    data = client.get("/balance").json()
    assert len(data) == 3
    assert all(item["status"] in {"OK", "VIOLATIONS", "NOT_ASSESSABLE"} for item in data)


def test_balance_unknown_facility_is_404(client):
    assert_error(client.get("/balance/FAC-999"), 404, "NOT_FOUND")


def test_detection_preview_raises_no_alarms(client):
    before = len(client.get("/alarms").json())
    response = client.get("/detection")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(client.get("/alarms").json()) == before


def test_detection_unknown_facility_is_404(client):
    assert_error(client.get("/detection", params={"facility_id": "FAC-999"}), 404, "NOT_FOUND")


def test_data_quality_reports_counts(client):
    body = client.get("/data-quality").json()
    assert body["overall"] in {"OK", "ISSUES"}
    counts = body["counts"]
    assert (counts["facilities"], counts["pumps"], counts["tanks"], counts["valves"]) == (3, 20, 30, 60)
    assert counts["telemetry"] > 0
    assert len(body["topology"]) == 3 and len(body["balance"]) == 3


# ---------- alarms and simulations: error cases ----------
def test_unknown_alarm_is_404(client):
    assert_error(client.get("/alarms/ALM-999999"), 404, "NOT_FOUND")


def test_unknown_alarm_state_filter_is_422(client):
    assert_error(client.get("/alarms", params={"state": "BOGUS"}), 422, "VALIDATION_FAILED")


def test_simulation_without_mode_is_422(client):
    assert_error(client.post("/simulations", json={}), 422, "VALIDATION_FAILED")


def test_simulation_unknown_mode_is_404(client):
    assert_error(client.post("/simulations", json={"mode_id": "MODE-999"}), 404, "NOT_FOUND")


def test_simulation_speed_out_of_range_is_422(client):
    body = {"mode_id": first_mode_id(client), "pump_speed_pct": 150}
    assert_error(client.post("/simulations", json=body), 422, "VALIDATION_FAILED")


def test_unknown_simulation_is_404(client):
    assert_error(client.get("/simulations/SIM-2026-999999"), 404, "NOT_FOUND")


# ---------- end to end ----------
def test_end_to_end_detect_alarm_lifecycle_and_simulation(client):
    # 1. Detect and raise alarms.
    run = client.post("/detection/run")
    assert run.status_code == 200
    first = run.json()
    assert first["events_found"] > 0
    assert first["alarms_created"] > 0

    # 2. Running again must not create duplicates.
    again = client.post("/detection/run").json()
    assert again["alarms_created"] == 0

    # 3. Alarm lifecycle: RAISED -> ACKNOWLEDGED -> CLEARED.
    alarm_id = first["alarms"][0]["alarm_id"]
    assert client.get(f"/alarms/{alarm_id}").json()["state"] == "RAISED"
    assert client.post(f"/alarms/{alarm_id}/acknowledge").json()["state"] == "ACKNOWLEDGED"
    cleared = client.post(f"/alarms/{alarm_id}/clear").json()
    assert cleared["state"] == "CLEARED" and cleared["cleared_at"] is not None

    history = client.get(f"/alarms/{alarm_id}/history").json()
    assert [h["new_state"] for h in history] == ["RAISED", "ACKNOWLEDGED", "CLEARED"]

    # 4. A cleared alarm cannot move again.
    assert_error(client.post(f"/alarms/{alarm_id}/acknowledge"), 422, "VALIDATION_FAILED")

    # 5. Simulation: 201, stored, and reproducible with the same input.
    body = {"mode_id": first_mode_id(client)}
    one = client.post("/simulations", json=body)
    two = client.post("/simulations", json=body)
    assert one.status_code == 201 and two.status_code == 201
    assert one.json()["simulation_id"] != two.json()["simulation_id"]
    assert one.json()["result"] == two.json()["result"]
    assert one.json()["assumptions"] == two.json()["assumptions"]

    fetched = client.get(f"/simulations/{one.json()['simulation_id']}")
    assert fetched.status_code == 200
    assert fetched.json() == one.json()
    assert len(client.get("/simulations").json()) >= 2