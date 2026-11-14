import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generator.anomalies import inject_anomalies
from generator.master_data import generate_master
from generator.sensors_modes import generate_sensors
from generator.telemetry import generate_baseline

SEED = 20261022


@pytest.fixture(scope="module")
def data():
    m = generate_master(SEED)
    s = generate_sensors(m, 100)
    b = generate_baseline(m, s, SEED, steps=1000)
    return s, b, inject_anomalies(b, s, SEED)


def test_baseline_is_not_mutated(data):
    s, b, _ = data
    m = generate_master(SEED)
    fresh = generate_baseline(m, s, SEED, steps=1000)
    for k in b["series"]:
        assert np.array_equal(b["series"][k], fresh["series"][k])


def test_ground_truth_has_expected_counts(data):
    _, _, r = data
    types = [t["issue_type"] for t in r["ground_truth"]]
    assert len(types) == 8
    for scen in ("LEAK", "BLOCKAGE", "PUMP_DEGRADATION", "SENSOR_FAULT"):
        assert types.count(scen) == 2


def test_scenarios_use_distinct_pumps(data):
    _, _, r = data
    comps = [t["component_id"] for t in r["ground_truth"]]
    assert len(comps) == len(set(comps))


def test_only_labelled_sensors_change(data):
    _, b, r = data
    changed = {k for k in b["series"] if not np.array_equal(b["series"][k], r["series"][k])}
    labelled = {sid for t in r["ground_truth"] for sid in t["sensor_ids"].split(";")}
    assert changed == labelled


def test_changes_happen_only_inside_window(data):
    _, b, r = data
    ts = b["timestamps"]
    for t in r["ground_truth"]:
        i0 = ts.index(__import__("datetime").datetime.fromisoformat(t["start_ts"]))
        i1 = ts.index(__import__("datetime").datetime.fromisoformat(t["end_ts"]))
        for sid in t["sensor_ids"].split(";"):
            diff = b["series"][sid] != r["series"][sid]
            idx = np.where(diff)[0]
            assert idx.size > 0 and idx.min() >= i0 and idx.max() <= i1


def test_sensor_fault_changes_only_one_sensor(data):
    _, _, r = data
    for t in r["ground_truth"]:
        n = len(t["sensor_ids"].split(";"))
        assert (n == 1) == (t["issue_type"] == "SENSOR_FAULT")


def test_ground_truth_is_separate_from_series(data):
    s, _, r = data
    assert "ground_truth" not in r["series"]
    assert set(r["series"]) == {x["sensor_id"] for x in s}


def test_deterministic(data):
    s, b, r = data
    r2 = inject_anomalies(b, s, SEED)
    assert r["ground_truth"] == r2["ground_truth"]


def test_too_many_scenarios_rejected(data):
    s, b, _ = data
    with pytest.raises(ValueError):
        inject_anomalies(b, s, SEED, per_type=50)