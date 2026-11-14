"""Validation checks. Pure functions: data in, list of issues out."""
import re

PATTERNS = {
    "facilities": ("facility_id", r"^FAC-\d{3}$"),
    "pumps": ("pump_id", r"^PUMP-\d{3}$"),
    "tanks": ("tank_id", r"^TANK-\d{3}$"),
    "valves": ("valve_id", r"^VALVE-\d{3}$"),
    "pipes": ("pipe_id", r"^PIPE-\d{3}$"),
}


def _issue(check, entity, rid, detail):
    return {"check": check, "entity": entity, "id": rid, "detail": detail}


def check_ids_and_uniqueness(master: dict) -> list[dict]:
    issues = []
    for entity, (key, pat) in PATTERNS.items():
        seen = set()
        for r in master[entity]:
            rid = r[key]
            if not re.match(pat, rid):
                issues.append(_issue("id_format", entity, rid, "bad ID format"))
            if rid in seen:
                issues.append(_issue("duplicate_id", entity, rid, "duplicate primary key"))
            seen.add(rid)
    return issues


def check_foreign_keys(master: dict) -> list[dict]:
    issues = []
    fids = {f["facility_id"] for f in master["facilities"]}
    for entity in ("pumps", "tanks", "valves", "pipes"):
        for r in master[entity]:
            if r["facility_id"] not in fids:
                issues.append(_issue("fk_facility", entity, r.get(PATTERNS[entity][0]), "missing facility"))
    return issues


def check_pipes(pipes: list[dict], master: dict) -> list[dict]:
    """Edge case 1: pipe endpoint must be a real node in the same facility."""
    node_fac = {}
    for key, idk in [("pumps", "pump_id"), ("tanks", "tank_id"), ("valves", "valve_id")]:
        for r in master[key]:
            node_fac[r[idk]] = r["facility_id"]
    issues = []
    for p in pipes:
        for end in (p["from_node_id"], p["to_node_id"]):
            if end not in node_fac:
                issues.append(_issue("pipe_missing_node", "pipe", p["pipe_id"], f"endpoint {end} does not exist"))
            elif node_fac[end] != p["facility_id"]:
                issues.append(_issue("pipe_cross_facility", "pipe", p["pipe_id"], f"{end} in another facility"))
    return issues


def check_tank_readings(readings: list[dict]) -> list[dict]:
    """Edge case 2: level above 100% (or below 0%)."""
    return [_issue("tank_over_capacity", "tank_reading", r["sensor_id"],
                   f"level {r['value']}% outside 0-{r['capacity_pct_limit']}%")
            for r in readings if r["value"] > r["capacity_pct_limit"] or r["value"] < 0]


def check_flow_balance(rows: list[dict]) -> list[dict]:
    """Edge case 3: |in - out - storage| must be within tolerance."""
    issues = []
    for r in rows:
        residual = abs(r["inflow_m3h"] - r["outflow_m3h"] - r["storage_change_m3h"])
        if residual > r["tolerance_m3h"]:
            issues.append(_issue("flow_conservation", "facility", r["facility_id"],
                                 f"residual {residual:.1f} m3/h > tolerance {r['tolerance_m3h']}"))
    return issues


def check_simulations(runs: list[dict]) -> list[dict]:
    """Edge case 4: every run needs an input configuration (mode_id)."""
    return [_issue("simulation_missing_input", "simulation_run", r["simulation_id"], "mode_id is missing")
            for r in runs if not r.get("mode_id")]


def classify_fault(flow_deviates: bool, pressure_deviates: bool) -> str:
    """Rule: both related sensors move = PROCESS fault; only one = SENSOR fault; none = NORMAL."""
    if flow_deviates and pressure_deviates:
        return "PROCESS_FAULT"
    if flow_deviates or pressure_deviates:
        return "SENSOR_FAULT"
    return "NORMAL"


def check_fault_labels(labels: list[dict], deviations: dict) -> list[dict]:
    """Edge case 5: stored label must match the classification rule.
    deviations: sensor_id -> (flow_deviates, pressure_deviates)."""
    issues = []
    for lab in labels:
        expected = classify_fault(*deviations[lab["sensor_id"]])
        if lab["stored_label"] != expected:
            issues.append(_issue("fault_mislabelled", "sensor", lab["sensor_id"],
                                 f"stored {lab['stored_label']}, rule says {expected}"))
    return issues