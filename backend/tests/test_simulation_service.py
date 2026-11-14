from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, make_engine
from app.core.errors import NotFoundError, ValidationFailure
from app.repositories.plant_repo import PlantRepository
from app.repositories.simulation_repo import SimulationRepository
from app.services.loader import load_seed
from app.services.simulation_service import SimulationService, steady_state
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"
PUMP = {"pump_id": "P1", "rated_flow_m3h": 100.0, "shutoff_head_m": 50.0, "curve_coeff_k": 0.001}
TANK = {"capacity_m3": 1000.0, "max_level_pct": 95.0}


def test_steady_state_numbers():
    r = steady_state([PUMP], {"V1": 100.0, "V2": 50.0}, [TANK], 100.0)
    assert r["inflow_m3h"] == 100.0
    assert r["pumps"][0]["head_m"] == 40.0
    assert r["pumps"][0]["pressure_kpa"] == pytest.approx(392.4)
    assert r["outflow_m3h"] == 75.0
    assert r["storage_change_m3h"] == 25.0
    assert r["hours_until_tanks_full"] == 18.0


def test_all_valves_closed_gives_warning_and_fill_time():
    r = steady_state([PUMP], {"V1": 0.0}, [TANK], 100.0)
    assert "ALL_VALVES_CLOSED" in r["warnings"]
    assert r["hours_until_tanks_full"] == 4.5


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "sim_test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    load_seed(engine, SEED_DIR)
    session = sessionmaker(bind=engine)()
    yield SimulationService(PlantRepository(session), SimulationRepository(session))
    session.close()
    engine.dispose()


def test_run_is_reproducible(service):
    a = service.run("MODE-001")
    b = service.run("MODE-001")
    assert a["result"] == b["result"]
    assert a["assumptions"] == b["assumptions"]
    assert a["simulation_id"] != b["simulation_id"]


def test_run_is_saved_with_assumptions_and_result(service):
    made = service.run("MODE-002")
    saved = service.get(made["simulation_id"])
    assert saved["mode_id"] == "MODE-002"
    assert saved["assumptions"]["pump_speed_pct"] == 55.0
    assert saved["result"]["inflow_m3h"] > 0
    assert saved["seed"] == 20261022


def test_missing_mode_id_rejected(service):
    with pytest.raises(ValidationFailure):
        service.run(None)
    with pytest.raises(ValidationFailure):
        service.run("")


def test_unknown_mode_not_found(service):
    with pytest.raises(NotFoundError):
        service.run("MODE-999")


def test_speed_override_changes_flow(service):
    base = service.run("MODE-001")
    slower = service.run("MODE-001", pump_speed_pct=40.0)
    assert slower["result"]["inflow_m3h"] < base["result"]["inflow_m3h"]
    assert slower["assumptions"]["pump_speed_pct"] == 40.0


def test_bad_speed_rejected(service):
    with pytest.raises(ValidationFailure):
        service.run("MODE-001", pump_speed_pct=120.0)


def test_valve_from_other_facility_rejected(service):
    with pytest.raises(ValidationFailure):
        service.run("MODE-001", valve_positions={"VALVE-050": 0.0})