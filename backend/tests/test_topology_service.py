from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, make_engine
from app.core.errors import NotFoundError
from app.repositories.plant_repo import PlantRepository
from app.services.loader import load_seed
from app.services.topology_service import TopologyService, analyse_graph
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


# ---------- pure graph tests ----------
def test_connected_graph():
    r = analyse_graph({"A", "B", "C"}, [("P1", "A", "B"), ("P2", "B", "C")])
    assert r["connected"] is True
    assert r["status"] == "OK"
    assert r["invalid_pipes"] == []


def test_disconnected_graph_reports_isolated_node():
    r = analyse_graph({"A", "B", "C"}, [("P1", "A", "B")])
    assert r["connected"] is False
    assert r["component_count"] == 2
    assert r["isolated_nodes"] == ["C"]
    assert r["status"] == "ISSUES"


def test_pipe_with_missing_node_is_reported():
    r = analyse_graph({"A", "B"}, [("P1", "A", "B"), ("P2", "B", "GHOST")])
    assert r["invalid_pipes"] == [{"pipe_id": "P2", "missing_nodes": ["GHOST"]}]
    assert r["status"] == "ISSUES"


def test_empty_facility_is_not_connected():
    assert analyse_graph(set(), [])["connected"] is False


# ---------- tests on the real loaded data ----------
@pytest.fixture(scope="module")
def service(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "topo_test.db"
    engine = make_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    load_seed(engine, SEED_DIR)
    session = sessionmaker(bind=engine)()
    yield TopologyService(PlantRepository(session))
    session.close()
    engine.dispose()


def test_all_three_facilities_are_connected_and_valid(service):
    results = service.check_all()
    assert len(results) == 3
    for r in results:
        assert r["connected"] is True, r
        assert r["invalid_pipes"] == [], r
        assert r["status"] == "OK"


def test_unknown_facility_raises_not_found(service):
    with pytest.raises(NotFoundError):
        service.check_facility("FAC-999")