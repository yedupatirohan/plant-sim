import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generator.edge_cases import build_edge_cases
from generator.master_data import generate_master
from generator.sensors_modes import generate_sensors
from generator.telemetry import generate_baseline
from generator.validators import (check_fault_labels, check_flow_balance, check_foreign_keys,
                                  check_ids_and_uniqueness, check_pipes, check_simulations,
                                  check_tank_readings, classify_fault)

SEED = 20261022


def setup():
    m = generate_master(SEED)
    s = generate_sensors(m, 100)
    b = generate_baseline(m, s, SEED, steps=1000)
    return m, s, build_edge_cases(m, s, b)["staging"]


def test_clean_master_has_no_issues():
    m, _, _ = setup()
    assert check_ids_and_uniqueness(m) == []
    assert check_foreign_keys(m) == []
    assert check_pipes(m["pipes"], m) == []


def test_detects_missing_pipe_node():
    m, _, st = setup()
    issues = check_pipes(st["pipes"], m)
    assert len(issues) == 1 and issues[0]["check"] == "pipe_missing_node"


def test_detects_tank_over_capacity():
    _, _, st = setup()
    assert [i["check"] for i in check_tank_readings(st["tank_readings"])] == ["tank_over_capacity"]


def test_tank_at_exact_limit_is_valid():
    ok = [{"sensor_id": "SNS-001", "value": 100.0, "capacity_pct_limit": 100.0}]
    assert check_tank_readings(ok) == []


def test_detects_flow_conservation_violation():
    _, _, st = setup()
    assert [i["check"] for i in check_flow_balance(st["flow_balance"])] == ["flow_conservation"]


def test_flow_exactly_at_tolerance_is_valid():
    row = {"facility_id": "FAC-001", "inflow_m3h": 100.0, "outflow_m3h": 90.0,
           "storage_change_m3h": 0.0, "tolerance_m3h": 10.0}
    assert check_flow_balance([row]) == []


def test_detects_simulation_without_input():
    _, _, st = setup()
    assert [i["check"] for i in check_simulations(st["simulation_runs"])] == ["simulation_missing_input"]


def test_valid_simulation_passes():
    ok = [{"simulation_id": "SIM-2026-000001", "mode_id": "MODE-001"}]
    assert check_simulations(ok) == []


def test_classification_rule():
    assert classify_fault(True, True) == "PROCESS_FAULT"
    assert classify_fault(True, False) == "SENSOR_FAULT"
    assert classify_fault(False, False) == "NORMAL"


def test_detects_sensor_fault_labelled_as_process_fault():
    _, _, st = setup()
    sid = st["sensor_fault_labels"][0]["sensor_id"]
    issues = check_fault_labels(st["sensor_fault_labels"], {sid: (True, False)})
    assert len(issues) == 1 and issues[0]["check"] == "fault_mislabelled"


def test_correct_label_passes():
    labels = [{"sensor_id": "SNS-001", "stored_label": "SENSOR_FAULT"}]
    assert check_fault_labels(labels, {"SNS-001": (True, False)}) == []


def test_detects_duplicate_and_bad_ids():
    m = generate_master(SEED)
    m["pumps"].append(dict(m["pumps"][0]))
    m["tanks"][0]["tank_id"] = "TNK-1"
    checks = {i["check"] for i in check_ids_and_uniqueness(m)}
    assert {"duplicate_id", "id_format"} <= checks