"""Response shape for detection metrics. Delays are in minutes."""
from pydantic import BaseModel


class TypeCounts(BaseModel):
    tp: int
    fp: int
    fn: int


class MatchOut(BaseModel):
    scenario_id: str
    alarm_type: str
    component_id: str
    detected_at: str
    delay_min: float


class FalsePositiveOut(BaseModel):
    component_id: str
    alarm_type: str
    start_ts: str
    end_ts: str


class EdgeCaseOut(BaseModel):
    scenario_id: str
    issue_type: str
    expected_alarm_type: str
    detected: bool


class NotScoredOut(BaseModel):
    scenario_id: str
    issue_type: str


class MetricsOut(BaseModel):
    truth_scenarios: int
    detections: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    f1: float | None
    mean_delay_min: float | None
    max_delay_min: float | None
    per_type: dict[str, TypeCounts]
    matches: list[MatchOut]
    missed: list[str]
    false_positive_events: list[FalsePositiveOut]
    edge_cases: list[EdgeCaseOut]
    not_scored_here: list[NotScoredOut]