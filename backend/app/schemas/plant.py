"""Response shapes for plant data. Field names carry their units."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class _Out(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FacilityOut(_Out):
    facility_id: str
    name: str
    status: str
    commissioned_on: date


class PumpOut(_Out):
    pump_id: str
    facility_id: str
    name: str
    rated_flow_m3h: float
    shutoff_head_m: float
    curve_coeff_k: float
    status: str
    effective_from: date
    effective_to: date | None


class TankOut(_Out):
    tank_id: str
    facility_id: str
    name: str
    capacity_m3: float
    cross_section_m2: float
    min_level_pct: float
    max_level_pct: float
    status: str


class ValveOut(_Out):
    valve_id: str
    facility_id: str
    name: str
    default_state: str
    default_position_pct: float


class PipeOut(_Out):
    pipe_id: str
    facility_id: str
    from_node_id: str
    to_node_id: str
    length_m: float
    diameter_mm: float


class SensorOut(_Out):
    sensor_id: str
    facility_id: str
    component_type: str
    component_id: str
    measurement: str
    unit: str


class ModeOut(_Out):
    mode_id: str
    facility_id: str
    name: str
    pump_speed_pct: float
    effective_from: datetime
    effective_to: datetime | None


class ComponentsOut(BaseModel):
    facility_id: str
    pumps: list[PumpOut]
    tanks: list[TankOut]
    valves: list[ValveOut]
    pipes: list[PipeOut]
    sensors: list[SensorOut]


class TelemetryPoint(BaseModel):
    ts_utc: datetime
    value: float
    quality: str


class TelemetryOut(BaseModel):
    sensor_id: str
    measurement: str
    unit: str
    count: int
    points: list[TelemetryPoint]