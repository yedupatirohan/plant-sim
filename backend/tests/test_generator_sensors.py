import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generator.master_data import generate_master
from generator.sensors_modes import (UNITS, generate_modes, generate_mode_valve_states,
                                     generate_sensors)

SEED = 20261022
START = datetime(2026, 1, 1)


def test_sensor_count_matches_target():
    m = generate_master(SEED)
    assert len(generate_sensors(m, 100)) == 100


def test_sensor_ids_unique_and_padded():
    s = generate_sensors(generate_master(SEED), 100)
    assert s[0]["sensor_id"] == "SNS-001" and s[-1]["sensor_id"] == "SNS-100"
    assert len({x["sensor_id"] for x in s}) == 100


def test_sensor_units_match_measurement():
    for s in generate_sensors(generate_master(SEED), 100):
        assert s["unit"] == UNITS[s["measurement"]]


def test_sensor_component_exists_in_same_facility():
    m = generate_master(SEED)
    comp = {}
    for key, idk in [("pumps", "pump_id"), ("tanks", "tank_id"), ("valves", "valve_id")]:
        for r in m[key]:
            comp[r[idk]] = r["facility_id"]
    for s in generate_sensors(m, 100):
        assert comp[s["component_id"]] == s["facility_id"]


def test_sensors_are_deterministic():
    m = generate_master(SEED)
    assert generate_sensors(m, 100) == generate_sensors(m, 100)


def test_modes_do_not_overlap_within_facility():
    m = generate_master(SEED)
    modes = generate_modes(m, START)
    assert len(modes) == 9
    for fac in m["facilities"]:
        mine = sorted((x for x in modes if x["facility_id"] == fac["facility_id"]),
                      key=lambda x: x["effective_from"])
        for a, b in zip(mine, mine[1:]):
            assert a["effective_to"] <= b["effective_from"]


def test_mode_valve_states_reference_valid_rows():
    m = generate_master(SEED)
    modes = generate_modes(m, START)
    rows = generate_mode_valve_states(m, modes)
    mode_ids = {x["mode_id"] for x in modes}
    valve_ids = {v["valve_id"] for v in m["valves"]}
    assert all(r["mode_id"] in mode_ids and r["valve_id"] in valve_ids for r in rows)
    assert len({(r["mode_id"], r["valve_id"]) for r in rows}) == len(rows)
    assert len(rows) == 60 * 3