import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from generator.build_dataset import build

SEED = 20261022


def test_two_runs_have_identical_checksums(tmp_path):
    a = build(SEED, tmp_path / "a")
    b = build(SEED, tmp_path / "b")
    assert a["files"] == b["files"]


def test_row_counts(tmp_path):
    m = build(SEED, tmp_path / "a")["files"]
    assert m["telemetry"]["rows"] == 100_000
    assert (m["facility"]["rows"], m["pump"]["rows"], m["tank"]["rows"], m["valve"]["rows"]) == (3, 20, 30, 60)
    assert m["ground_truth_csv"]["rows"] == 13  # 8 anomalies + 5 edge cases


def test_ground_truth_is_in_separate_folder(tmp_path):
    out = tmp_path / "a"
    build(SEED, out)
    assert (out / "ground_truth" / "ground_truth.csv").exists()
    assert not (out / "ground_truth.csv").exists()


def test_input_files_do_not_leak_labels(tmp_path):
    out = tmp_path / "a"
    build(SEED, out)
    with open(out / "telemetry.csv", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == ["telemetry_id", "sensor_id", "ts_utc", "value", "quality"]
    text = (out / "telemetry.csv").read_text(encoding="utf-8")
    for word in ("LEAK", "BLOCKAGE", "issue_type", "ground_truth"):
        assert word not in text


def test_telemetry_foreign_keys_and_unique_ids(tmp_path):
    out = tmp_path / "a"
    build(SEED, out)
    with open(out / "sensor.csv", encoding="utf-8") as f:
        sensor_ids = {r["sensor_id"] for r in csv.DictReader(f)}
    ids, pairs = set(), set()
    with open(out / "telemetry.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            assert r["sensor_id"] in sensor_ids
            ids.add(r["telemetry_id"])
            pairs.add((r["sensor_id"], r["ts_utc"]))
    assert len(ids) == len(pairs) == 100_000


def test_manifest_written_and_ground_truth_json_valid(tmp_path):
    out = tmp_path / "a"
    build(SEED, out)
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["seed"] == SEED and "telemetry" in man["files"]
    gt = json.loads((out / "ground_truth" / "ground_truth.json").read_text(encoding="utf-8"))
    assert len(gt) == 13