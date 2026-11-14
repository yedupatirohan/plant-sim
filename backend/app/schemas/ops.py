"""Response and request shapes for topology, balance, detection, alarms, simulation."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class InvalidPipe(BaseModel):
    pipe_id: str
    missing_nodes: list[str]


class TopologyOut(BaseModel):
    facility_id: str
    node_count: int
    pipe_count: int
    component_count: int
    connected: bool
    isolated_nodes: list[str]
    invalid_pipes: list[InvalidPipe]
    status: str


class BalanceEvent(BaseModel):
    start_ts: str
    end_ts: str
    max_residual_m3h: float


class BalanceOut(BaseModel):
    facility_id: str
    status: str
    note: str | None
    windows_checked: int
    violation_windows: int
    events: list[BalanceEvent]


class DetectionEventOut(BaseModel):
    facility_id: str
    component_type: str
    component_id: str
    alarm_type: str
    sensor_ids: list[str]
    start_ts: str
    end_ts: str
    detected_at: str


class AlarmOut(BaseModel):
    alarm_id: str
    facility_id: str
    sensor_id: str | None
    alarm_type: str
    state: str
    raised_at: str
    cleared_at: str | None


class AlarmEventOut(BaseModel):
    old_state: str | None
    new_state: str
    changed_at: str


class AlarmChangeIn(BaseModel):
    at: datetime | None = None


class DetectRunOut(BaseModel):
    events_found: int
    alarms_created: int
    alarms: list[AlarmOut]


class SimulationIn(BaseModel):
    mode_id: str | None = None          # missing -> service answers 422
    pump_speed_pct: float | None = None
    valve_positions: dict[str, float] | None = None


class SimulationOut(BaseModel):
    simulation_id: str
    mode_id: str
    seed: int
    status: str
    assumptions: dict[str, Any]
    result: dict[str, Any]


class DataQualityOut(BaseModel):
    overall: str
    counts: dict[str, int]
    telemetry_from: datetime | None
    telemetry_to: datetime | None
    topology: list[TopologyOut]
    balance: list[BalanceOut]