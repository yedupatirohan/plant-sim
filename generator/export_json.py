"""Write JSON copies of the data tables. Derived from the CSV files; deterministic."""
import argparse
import csv
import json
import re
from pathlib import Path

TABLES = ["facility", "pump", "tank", "valve", "pipe", "sensor",
          "operating_mode", "operating_mode_valve_state", "telemetry"]

_INT = re.compile(r"^-?(0|[1-9]\d*)$")
_FLOAT = re.compile(r"^-?\d+\.\d+$")


def _convert(value: str):
    """CSV gives text; turn empty into null and numbers into numbers. IDs stay text."""
    if value == "":
        return None
    if _INT.match(value):
        return int(value)
    if _FLOAT.match(value):
        return float(value)
    return value


def export_json(seed_dir: Path, out_dir: Path) -> dict:
    seed_dir, out_dir = Path(seed_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for table in TABLES:
        with open(seed_dir / f"{table}.csv", newline="", encoding="utf-8") as f:
            rows = [{k: _convert(v) for k, v in row.items()} for row in csv.DictReader(f)]
        if len(rows) > 5000:
            text = json.dumps(rows, separators=(",", ":"))
        else:
            text = json.dumps(rows, indent=2)
        (out_dir / f"{table}.json").write_text(text + "\n", encoding="utf-8", newline="\n")
        counts[table] = len(rows)
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description="Export the data tables as JSON")
    ap.add_argument("--data", default="data/seed")
    ap.add_argument("--out", default="data/json")
    a = ap.parse_args()
    counts = export_json(Path(a.data), Path(a.out))
    for table, n in counts.items():
        print(f"{table}: {n} rows")
    print(f"Written {len(counts)} JSON files to {a.out}")


if __name__ == "__main__":
    main()