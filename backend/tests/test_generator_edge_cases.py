import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generator.edge_cases import build_edge_cases
from generator.master_data import generate_master
from generator.sensors_modes import generate_sensors
from generator.telemetry import generate_baseline

SEED = 20261022


def build():
    m = generate_master(SEED)
    s = generate_sensors(m, 100)
    b = generate_baseline(m, s, SEED, steps=1000)
    return m, s, build_edge_cases(m, s, b)


def test_five_edge_cases_labelled():
    _, _, e = build()
    assert [g["scenario_id"] for g in e["ground_truth"]] == [f"EDGE-00{i}" for i in range(1, 6)]


def test_pipe_references_missing_node():
    m, _, e = build()
    nodes = {r[k] for key, k in [("pumps", "pump_id"), ("tanks", "tank_id"), ("valves", "valve_id")] for r in m[key]}
    assert e["staging"]["pipes"][0]["to_node_id"] not in nodes


def test_tank_level_exceeds_capacity():
    _, _, e = build()
    r = e["staging"]["tank_readings"][0]
    assert r["value"] > r["capacity_pct_limit"]


def test_flow_conservation_violated_beyond_tolerance():
    _, _, e = build()
    f = e["staging"]["flow_balance"][0]
    residual = abs(f["inflow_m3h"] - f["outflow_m3h"] - f["storage_change_m3h"])
    assert residual > f["tolerance_m3h"]


def test_simulation_lacks_input_configuration():
    _, _, e = build()
    assert e["staging"]["simulation_runs"][0]["mode_id"] is None


def test_sensor_fault_mislabelled_as_process_fault():
    _, _, e = build()
    assert e["staging"]["sensor_fault_labels"][0]["stored_label"] == "PROCESS_FAULT"
    assert e["ground_truth"][4]["expected_alarm_type"] == "SENSOR_FAULT"


def test_main_master_data_untouched():
    m, _, _ = build()
    assert m == generate_master(SEED)