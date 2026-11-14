"""Scores detection events against the labelled ground truth (business logic)."""
from datetime import datetime

from app.repositories.ground_truth_repo import GroundTruthRepository
from app.services.detection_service import DetectionService

# Alarm types the pump/tank detector can produce. Other labels (MASS_BALANCE,
# topology, simulation input) are checked by their own services.
DETECTOR_TYPES = {"LEAK", "BLOCKAGE", "PUMP_DEGRADATION", "SENSOR_FAULT", "OVERFLOW"}


def _t(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _same_target(event: dict, row: dict) -> bool:
    """The truth row names a component (PUMP-003) or a sensor (SNS-031)."""
    target = row["component_id"]
    return event["component_id"] == target or target in event.get("sensor_ids", [])


def _overlaps(event: dict, row: dict) -> bool:
    return _t(event["start_ts"]) <= _t(row["end_ts"]) and _t(event["end_ts"]) >= _t(row["start_ts"])


def _ratio(top: int, bottom: int) -> float | None:
    return top / bottom if bottom else None


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def score(events: list[dict], truth: list[dict]) -> dict:
    """Pure function. events come from DetectionService, truth from the CSV."""
    timed = [r for r in truth
             if r.get("start_ts") and r.get("end_ts") and r.get("expected_alarm_type")]
    edges = [r for r in truth
             if not r.get("start_ts") and r.get("expected_alarm_type") in DETECTOR_TYPES]
    scored_ids = {r["scenario_id"] for r in timed + edges}
    not_scored = [{"scenario_id": r["scenario_id"], "issue_type": r["issue_type"]}
                  for r in truth if r["scenario_id"] not in scored_ids]

    ordered = sorted(events, key=lambda e: (e["start_ts"], e["component_id"], e["alarm_type"]))
    per_type: dict[str, dict[str, int]] = {}

    def bump(kind: str, key: str) -> None:
        per_type.setdefault(kind, {"tp": 0, "fp": 0, "fn": 0})[key] += 1

    used: set[int] = set()
    matches, missed, delays = [], [], []
    for row in timed:
        kind = row["expected_alarm_type"]
        found = next((i for i, ev in enumerate(ordered)
                      if i not in used and ev["alarm_type"] == kind
                      and _same_target(ev, row) and _overlaps(ev, row)), None)
        if found is None:
            missed.append(row["scenario_id"])
            bump(kind, "fn")
            continue
        used.add(found)
        ev = ordered[found]
        delay = round((_t(ev["detected_at"]) - _t(row["start_ts"])).total_seconds() / 60, 1)
        delays.append(delay)
        bump(kind, "tp")
        matches.append({"scenario_id": row["scenario_id"], "alarm_type": kind,
                        "component_id": row["component_id"],
                        "detected_at": ev["detected_at"], "delay_min": delay})

    false_positives = []
    for i, ev in enumerate(ordered):
        if i in used:
            continue
        if any(ev["alarm_type"] == e["expected_alarm_type"] and _same_target(ev, e)
               for e in edges):
            continue  # explained by a labelled edge case
        false_positives.append({"component_id": ev["component_id"],
                                "alarm_type": ev["alarm_type"],
                                "start_ts": ev["start_ts"], "end_ts": ev["end_ts"]})
        bump(ev["alarm_type"], "fp")

    edge_cases = [{"scenario_id": e["scenario_id"], "issue_type": e["issue_type"],
                   "expected_alarm_type": e["expected_alarm_type"],
                   "detected": any(ev["alarm_type"] == e["expected_alarm_type"]
                                   and _same_target(ev, e) for ev in ordered)}
                  for e in edges]

    tp, fp, fn = len(matches), len(false_positives), len(missed)
    precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None and precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "truth_scenarios": len(timed),
        "detections": len(ordered),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": _round(precision),
        "recall": _round(recall),
        "f1": _round(f1),
        "mean_delay_min": round(sum(delays) / len(delays), 1) if delays else None,
        "max_delay_min": max(delays) if delays else None,
        "per_type": per_type,
        "matches": matches,
        "missed": missed,
        "false_positive_events": false_positives,
        "edge_cases": edge_cases,
        "not_scored_here": not_scored,
    }


class MetricsService:
    def __init__(self, detection: DetectionService, truth: GroundTruthRepository):
        self.detection = detection
        self.truth = truth

    def evaluate(self) -> dict:
        return score(self.detection.detect(), self.truth.load())