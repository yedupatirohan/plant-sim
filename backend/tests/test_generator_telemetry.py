import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generator.master_data import generate_master
from generator.sensors_modes import generate_sensors
from generator.telemetry import generate_baseline

SEED = 20261022


def build(steps=1000, seed=SEED):
    m = generate_master(seed)
    s = generate_sensors(m, 100)
    return m, s, generate_baseline(m, s, seed, steps=steps)


def test_total_points_is_100000():
    _, s, t = build()
    assert sum(len(v) for v in t["series"].values()) == 100_000
    assert len(t["timestamps"]) == 1000
    assert set(t["series"]) == {x["sensor_id"] for x in s}


def test_same_seed_is_identical():
    _, _, a = build()
    _, _, b = build()
    for sid in a["series"]:
        assert np.array_equal(a["series"][sid], b["series"][sid])


def test_different_seed_differs():
    _, _, a = build()
    _, _, b = build(seed=SEED + 1)
    assert any(not np.array_equal(a["series"][k], b["series"][k]) for k in a["series"])


def test_tank_levels_stay_within_physical_range():
    m, s, t = build()
    for sensor in s:
        if sensor["measurement"] == "LEVEL":
            vals = t["series"][sensor["sensor_id"]]
            assert vals.min() >= 0 and vals.max() <= 100


def test_flows_and_pressures_are_not_negative_beyond_noise():
    _, s, t = build()
    for sensor in s:
        if sensor["measurement"] in ("FLOW", "PRESSURE"):
            assert t["series"][sensor["sensor_id"]].min() > -10


def test_values_vary_over_time():
    _, s, t = build()
    pump_flow = next(x for x in s if x["component_type"] == "PUMP" and x["measurement"] == "FLOW")
    assert t["series"][pump_flow["sensor_id"]].std() > 1.0


def test_timestamps_are_one_minute_apart_and_ordered():
    _, _, t = build()
    ts = t["timestamps"]
    assert all((b - a).total_seconds() == 60 for a, b in zip(ts, ts[1:]))


def test_small_run_uses_same_generator():
    _, s, t = build(steps=50)
    assert sum(len(v) for v in t["series"].values()) == 100 * 50