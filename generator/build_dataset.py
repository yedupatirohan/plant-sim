"""Build the full dataset: CSV, JSON, SQL, ground truth, manifest. Deterministic."""
import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

from generator.anomalies import inject_anomalies
from generator.edge_cases import build_edge_cases
from generator.master_data import FULL_SCALE, generate_master
from generator.sensors_modes import (generate_modes, generate_mode_valve_states,
                                     generate_sensors)
from generator.telemetry import generate_baseline

START = datetime(2026, 1, 1)


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sql_value(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def _write_sql(path: Path, tables: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Generated seed data. Run after creating the schema.\n")
        for name, (rows, fields) in tables.items():
            for r in rows:
                cols = ", ".join(fields)
                vals = ", ".join(_sql_value(r[c]) for c in fields)
                f.write(f"INSERT INTO {name} ({cols}) VALUES ({vals});\n")


def build(seed: int, out: Path, steps: int = 1000, sensors_n: int = 100,
          scale: dict | None = None) -> dict:
    out = Path(out)
    gt_dir = out.parent / "ground_truth" if out.name == "seed" else out / "ground_truth"
    out.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)

    master = generate_master(seed, scale or FULL_SCALE)
    sensors = generate_sensors(master, sensors_n)
    modes = generate_modes(master, START)
    mode_valves = generate_mode_valve_states(master, modes)
    base = generate_baseline(master, sensors, seed, steps=steps, start=START)
    injected = inject_anomalies(base, sensors, seed)
    edge = build_edge_cases(master, sensors, base)

    # Telemetry rows in fixed order: sensor, then time
    ts = base["timestamps"]
    telemetry, n = [], 0
    for s in sensors:
        vals = injected["series"][s["sensor_id"]]
        for i, t in enumerate(ts):
            n += 1
            telemetry.append({"telemetry_id": f"TEL-{n:06d}", "sensor_id": s["sensor_id"],
                              "ts_utc": t.isoformat(), "value": f"{float(vals[i]):.3f}",
                              "quality": "GOOD"})

    tables = {
        "facility": (master["facilities"], ["facility_id", "name", "status", "commissioned_on"]),
        "pump": (master["pumps"], ["pump_id", "facility_id", "name", "rated_flow_m3h", "shutoff_head_m",
                                   "curve_coeff_k", "status", "effective_from", "effective_to"]),
        "tank": (master["tanks"], ["tank_id", "facility_id", "name", "capacity_m3", "cross_section_m2",
                                   "min_level_pct", "max_level_pct", "status"]),
        "valve": (master["valves"], ["valve_id", "facility_id", "name", "default_state",
                                     "default_position_pct"]),
        "pipe": (master["pipes"], ["pipe_id", "facility_id", "from_node_id", "to_node_id",
                                   "length_m", "diameter_mm"]),
        "sensor": (sensors, ["sensor_id", "facility_id", "component_type", "component_id",
                             "measurement", "unit"]),
        "operating_mode": (modes, ["mode_id", "facility_id", "name", "pump_speed_pct",
                                   "effective_from", "effective_to"]),
        "operating_mode_valve_state": (mode_valves, ["mode_id", "valve_id", "state", "position_pct"]),
        "telemetry": (telemetry, ["telemetry_id", "sensor_id", "ts_utc", "value", "quality"]),
    }

    files = []
    for name, (rows, fields) in tables.items():
        _write_csv(out / f"{name}.csv", rows, fields)
        files.append((name, out / f"{name}.csv", len(rows)))
    _write_sql(out / "seed.sql", tables)
    files.append(("seed_sql", out / "seed.sql", sum(len(r) for r, _ in tables.values())))

    gt = injected["ground_truth"] + edge["ground_truth"]
    gt_fields = ["scenario_id", "issue_type", "component_id", "sensor_ids", "start_ts", "end_ts",
                 "expected_alarm_type", "rule_applied"]
    gt_rows = [{k: r.get(k, "") for k in gt_fields} for r in gt]
    _write_csv(gt_dir / "ground_truth.csv", gt_rows, gt_fields)
    (gt_dir / "ground_truth.json").write_text(json.dumps(gt_rows, indent=2), encoding="utf-8", newline="\n")
    (out / "staging_edge_cases.json").write_text(
        json.dumps(edge["staging"], indent=2, sort_keys=True), encoding="utf-8", newline="\n")
    files += [("ground_truth_csv", gt_dir / "ground_truth.csv", len(gt_rows)),
              ("ground_truth_json", gt_dir / "ground_truth.json", len(gt_rows)),
              ("staging_edge_cases", out / "staging_edge_cases.json", 5)]

    manifest = {"seed": seed, "steps": steps, "sensors": sensors_n,
                "files": {name: {"path": p.name, "rows": rows, "sha256": _sha256(p)}
                          for name, p, rows in files}}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True),
                                       encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the plant dataset")
    ap.add_argument("--seed", type=int, default=20261022)
    ap.add_argument("--out", default="data/seed")
    ap.add_argument("--steps", type=int, default=1000)
    ap.add_argument("--sensors", type=int, default=100)
    a = ap.parse_args()
    m = build(a.seed, Path(a.out), a.steps, a.sensors)
    print(f"Built {len(m['files'])} files into {a.out}")
    print(f"telemetry rows: {m['files']['telemetry']['rows']}")


if __name__ == "__main__":
    main()