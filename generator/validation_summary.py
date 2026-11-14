"""Validation summary: runs the validators on the shipped files and writes a JSON report."""
import argparse
import csv
import json
from pathlib import Path

from generator import validators as v

ENTITY_FILES = {"facilities": "facility.csv", "pumps": "pump.csv", "tanks": "tank.csv",
                "valves": "valve.csv", "pipes": "pipe.csv"}

EDGE_CHECKS = {
    "EDGE-001": "pipe_missing_node",
    "EDGE-002": "tank_over_capacity",
    "EDGE-003": "flow_conservation",
    "EDGE-004": "simulation_missing_input",
    "EDGE-005": "fault_mislabelled",
}

# Words that only belong in the separate ground-truth files.
LEAK_MARKERS = ["scenario_id", "issue_type", "expected_alarm_type", "rule_applied", "EDGE-", "SCN-"]


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _count(issues: list[dict], check: str) -> int:
    return sum(1 for i in issues if i["check"] == check)


def scan_for_leaks(seed_dir: Path) -> dict:
    """Ground truth must never appear in the data files (manifest.json only names the files)."""
    leaks, scanned = [], 0
    for p in sorted(seed_dir.iterdir()):
        if not p.is_file() or p.name == "manifest.json":
            continue
        scanned += 1
        text = p.read_text(encoding="utf-8")
        if any(marker in text for marker in LEAK_MARKERS):
            leaks.append(p.name)
    return {"files_scanned": scanned, "leaks": leaks}


def build_summary(seed_dir: Path, staging: dict | None = None) -> dict:
    seed_dir = Path(seed_dir)
    master = {entity: _read_csv(seed_dir / fname) for entity, fname in ENTITY_FILES.items()}
    manifest = json.loads((seed_dir / "manifest.json").read_text(encoding="utf-8"))
    if staging is None:
        staging = json.loads((seed_dir / "staging_edge_cases.json").read_text(encoding="utf-8"))

    baseline_issues = {
        "id_format_and_uniqueness": v.check_ids_and_uniqueness(master),
        "foreign_keys": v.check_foreign_keys(master),
        "pipe_endpoints": v.check_pipes(master["pipes"], master),
    }

    # The staged label says only ONE sensor deviates (flow yes, pressure no).
    deviations = {lab["sensor_id"]: (True, False) for lab in staging["sensor_fault_labels"]}
    edge_issues = {
        "EDGE-001": v.check_pipes(staging["pipes"], master),
        "EDGE-002": v.check_tank_readings(staging["tank_readings"]),
        "EDGE-003": v.check_flow_balance(staging["flow_balance"]),
        "EDGE-004": v.check_simulations(staging["simulation_runs"]),
        "EDGE-005": v.check_fault_labels(staging["sensor_fault_labels"], deviations),
    }

    edge_cases = {}
    for edge_id, check in EDGE_CHECKS.items():
        found = _count(edge_issues[edge_id], check)
        edge_cases[edge_id] = {"check": check, "issues_found": found, "detected": found >= 1}

    leak_scan = scan_for_leaks(seed_dir)
    baseline = {name: {"issues": len(issues)} for name, issues in baseline_issues.items()}
    all_passed = (all(b["issues"] == 0 for b in baseline.values())
                  and all(e["detected"] for e in edge_cases.values())
                  and not leak_scan["leaks"])

    return {
        "seed": manifest["seed"],
        "row_counts": {entity: len(rows) for entity, rows in master.items()},
        "baseline_checks": baseline,
        "edge_cases": edge_cases,
        "ground_truth_leak_scan": leak_scan,
        "all_passed": all_passed,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Write the validation summary")
    ap.add_argument("--data", default="data/seed")
    ap.add_argument("--out", default="data/validation_summary.json")
    a = ap.parse_args()
    s = build_summary(Path(a.data))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(s, indent=2, sort_keys=True), encoding="utf-8", newline="\n")

    print(f"Validation summary (seed {s['seed']})")
    print("Row counts:", ", ".join(f"{k}={n}" for k, n in s["row_counts"].items()))
    print("Baseline checks:")
    for name, b in s["baseline_checks"].items():
        print(f"  {name}: {b['issues']} issues")
    print("Edge cases:")
    for edge_id, e in s["edge_cases"].items():
        state = "detected" if e["detected"] else "NOT DETECTED"
        print(f"  {edge_id} {e['check']}: {e['issues_found']} found -> {state}")
    leak = s["ground_truth_leak_scan"]
    print(f"Ground-truth leak scan: {leak['files_scanned']} files scanned, {len(leak['leaks'])} leaks")
    print("RESULT:", "PASSED" if s["all_passed"] else "FAILED")
    print(f"Written to {a.out}")
    raise SystemExit(0 if s["all_passed"] else 1)


if __name__ == "__main__":
    main()