"""Tests for the JSON export (derived from the CSV files in data/seed)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generator.export_json import TABLES, export_json  # noqa: E402

SEED_DIR = ROOT / "data" / "seed"


@pytest.fixture(scope="module")
def out_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("json_export")
    export_json(SEED_DIR, out)
    return out


def _load(out_dir, table):
    return json.loads((out_dir / f"{table}.json").read_text(encoding="utf-8"))


def test_writes_one_file_per_table(out_dir):
    assert {p.name for p in out_dir.iterdir()} == {f"{t}.json" for t in TABLES}


def test_row_counts_match_manifest(out_dir):
    manifest = json.loads((SEED_DIR / "manifest.json").read_text(encoding="utf-8"))
    for table in TABLES:
        assert len(_load(out_dir, table)) == manifest["files"][table]["rows"], table


def test_ids_stay_text_and_numbers_become_numbers(out_dir):
    pump = _load(out_dir, "pump")[0]
    assert pump["pump_id"].startswith("PUMP-")
    assert isinstance(pump["rated_flow_m3h"], (int, float))
    reading = _load(out_dir, "telemetry")[0]
    assert reading["telemetry_id"].startswith("TEL-")
    assert isinstance(reading["value"], float)


def test_export_is_deterministic(out_dir, tmp_path):
    export_json(SEED_DIR, tmp_path)
    for table in TABLE_NAMES_FOR_COMPARE():
        assert (tmp_path / f"{table}.json").read_bytes() == (out_dir / f"{table}.json").read_bytes()


def TABLE_NAMES_FOR_COMPARE():
    return TABLES