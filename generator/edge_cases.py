"""Five required edge cases as labelled staging records. Main data is never altered."""
import json


def build_edge_cases(master: dict, sensors: list[dict], baseline: dict) -> dict:
    ts0 = baseline["timestamps"][0].isoformat()
    tank = master["tanks"][0]
    pump = master["pumps"][0]
    fac_id = master["facilities"][0]["facility_id"]
    flow_sensor = next(s for s in sensors if s["component_id"] == pump["pump_id"] and s["measurement"] == "FLOW")

    staging = {
        "pipes": [{
            "pipe_id": "PIPE-901", "facility_id": fac_id,
            "from_node_id": tank["tank_id"], "to_node_id": "VALVE-999",
            "length_m": 50.0, "diameter_mm": 150.0,
        }],
        "tank_readings": [{
            "sensor_id": next(s["sensor_id"] for s in sensors if s["component_id"] == tank["tank_id"]),
            "ts_utc": ts0, "value": 112.5, "capacity_pct_limit": 100.0,
        }],
        "flow_balance": [{
            "facility_id": fac_id, "ts_utc": ts0,
            "inflow_m3h": 500.0, "outflow_m3h": 380.0, "storage_change_m3h": 5.0,
            "tolerance_m3h": 10.0,
        }],
        "simulation_runs": [{
            "simulation_id": "SIM-2026-900001", "mode_id": None, "seed": 20261022,
            "assumptions_json": json.dumps({}), "result_json": json.dumps({"flow": 100}),
            "status": "COMPLETED",
        }],
        "sensor_fault_labels": [{
            "sensor_id": flow_sensor["sensor_id"], "ts_utc": ts0,
            "stored_label": "PROCESS_FAULT", "reason": "single sensor deviates, neighbours normal",
        }],
    }

    ground_truth = [
        {"scenario_id": "EDGE-001", "issue_type": "PIPE_MISSING_NODE", "component_id": "PIPE-901",
         "expected_alarm_type": "", "rule_applied": "pipe endpoint VALVE-999 does not exist"},
        {"scenario_id": "EDGE-002", "issue_type": "TANK_LEVEL_EXCEEDS_CAPACITY", "component_id": tank["tank_id"],
         "expected_alarm_type": "OVERFLOW", "rule_applied": "level 112.5% > 100%"},
        {"scenario_id": "EDGE-003", "issue_type": "FLOW_CONSERVATION_VIOLATED", "component_id": fac_id,
         "expected_alarm_type": "MASS_BALANCE",
         "rule_applied": "|in - out - storage| = 115 > tolerance 10"},
        {"scenario_id": "EDGE-004", "issue_type": "SIMULATION_MISSING_INPUT", "component_id": "SIM-2026-900001",
         "expected_alarm_type": "", "rule_applied": "mode_id is null"},
        {"scenario_id": "EDGE-005", "issue_type": "SENSOR_FAULT_MISLABELLED", "component_id": flow_sensor["sensor_id"],
         "expected_alarm_type": "SENSOR_FAULT",
         "rule_applied": "only one sensor affected, so it is a sensor fault, not a process fault"},
    ]
    return {"staging": staging, "ground_truth": ground_truth}