"""Tests for the validation summary (reads the shipped files in data/seed)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generator.validation_summary import EDGE_CHECKS, build_summary  # noqa: E402

SEED_DIR = ROOT / "data" / "seed"


@pytest.fixture(scope="module")
def summary():
    return build_summary(SEED_DIR)


def test_baseline_has_no_issues(summary):
    for name, result in summary["baseline_checks"].items():
        assert result["issues"] == 0, name


def test_all_five_edge_cases_are_detected(summary):
    assert set(summary["edge_cases"]) == set(EDGE_CHECKS)
    for edge_id, result in summary["edge_cases"].items():
        assert result["detected"] is True, edge_id


def test_edge_cases_use_the_expected_checks(summary):
    for edge_id, check in EDGE_CHECKS.items():
        assert summary["edge_cases"][edge_id]["check"] == check


def test_no_ground_truth_leak_in_data_files(summary):
    assert summary["ground_truth_leak_scan"]["files_scanned"] >= 11
    assert summary["ground_truth_leak_scan"]["leaks"] == []


def test_overall_result_passed(summary):
    assert summary["all_passed"] is True


def test_summary_is_deterministic(summary):
    assert build_summary(SEED_DIR) == summary


def test_edge_case_check_clears_when_input_is_fixed():
    staging = json.loads((SEED_DIR / "staging_edge_cases.json").read_text(encoding="utf-8"))
    staging["simulation_runs"][0]["mode_id"] = "MODE-001"
    result = build_summary(SEED_DIR, staging=staging)
    assert result["edge_cases"]["EDGE-004"]["detected"] is False
    assert result["all_passed"] is False