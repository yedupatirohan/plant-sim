import csv
import shutil
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import make_engine
from app.models import Pump, Telemetry
from app.services.loader import load_seed
from generator.build_dataset import build

SEED = 20261022


@pytest.fixture(scope="module")
def seed_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("seed") / "seed"
    build(SEED, d)
    return d


def test_full_load_counts(seed_dir):
    engine = make_engine("sqlite:///:memory:")
    counts = load_seed(engine, seed_dir)
    assert counts["telemetry"] == 100_000
    with engine.connect() as c:
        assert c.execute(select(func.count()).select_from(Telemetry)).scalar() == 100_000
        assert c.execute(select(func.count()).select_from(Pump)).scalar() == 20


def test_foreign_key_integrity_after_load(seed_dir):
    engine = make_engine("sqlite:///:memory:")
    load_seed(engine, seed_dir)
    with engine.connect() as c:
        assert c.execute(text("PRAGMA foreign_key_check")).fetchall() == []


def test_bad_row_rolls_back_everything(seed_dir, tmp_path):
    bad = tmp_path / "bad"
    shutil.copytree(seed_dir, bad)
    rows = list(csv.DictReader(open(bad / "pump.csv", encoding="utf-8")))
    rows[0]["facility_id"] = "FAC-999"
    with open(bad / "pump.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    engine = make_engine("sqlite:///:memory:")
    with pytest.raises(IntegrityError):
        load_seed(engine, bad)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM facility")).scalar() == 0