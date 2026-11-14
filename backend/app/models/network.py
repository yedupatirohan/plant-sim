from sqlalchemy import (CheckConstraint, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Pipe(Base):
    __tablename__ = "pipe"

    pipe_id: Mapped[str] = mapped_column(String, primary_key=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facility.facility_id"), nullable=False)
    from_node_id: Mapped[str] = mapped_column(String, nullable=False)
    to_node_id: Mapped[str] = mapped_column(String, nullable=False)
    length_m: Mapped[float] = mapped_column(Float, nullable=False)
    diameter_mm: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("from_node_id <> to_node_id", name="ck_pipe_distinct_nodes"),
        CheckConstraint("length_m > 0", name="ck_pipe_length"),
        CheckConstraint("diameter_mm > 0", name="ck_pipe_diameter"),
        Index("ix_pipe_facility", "facility_id"),
    )


class Sensor(Base):
    __tablename__ = "sensor"

    sensor_id: Mapped[str] = mapped_column(String, primary_key=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facility.facility_id"), nullable=False)
    component_type: Mapped[str] = mapped_column(String, nullable=False)
    component_id: Mapped[str] = mapped_column(String, nullable=False)
    measurement: Mapped[str] = mapped_column(String, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("component_type IN ('PUMP','TANK','VALVE','PIPE')", name="ck_sensor_component_type"),
        CheckConstraint("measurement IN ('FLOW','PRESSURE','LEVEL')", name="ck_sensor_measurement"),
        CheckConstraint(
            "(measurement='FLOW' AND unit='m3/h') OR (measurement='PRESSURE' AND unit='kPa') "
            "OR (measurement='LEVEL' AND unit='%')",
            name="ck_sensor_unit_matches",
        ),
        Index("ix_sensor_facility", "facility_id"),
        Index("ix_sensor_component", "component_id"),
    )


class OperatingMode(Base):
    __tablename__ = "operating_mode"

    mode_id: Mapped[str] = mapped_column(String, primary_key=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facility.facility_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    pump_speed_pct: Mapped[float] = mapped_column(Float, nullable=False)
    effective_from: Mapped[str] = mapped_column(DateTime, nullable=False)
    effective_to: Mapped[str | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("name IN ('NORMAL','LOW_DEMAND','PEAK_DEMAND','MAINTENANCE')", name="ck_mode_name"),
        CheckConstraint("pump_speed_pct >= 0 AND pump_speed_pct <= 100", name="ck_mode_speed"),
        CheckConstraint("effective_to IS NULL OR effective_from < effective_to", name="ck_mode_dates"),
        Index("ix_mode_facility", "facility_id"),
    )


class OperatingModeValveState(Base):
    """Bridge table (N:M) between OperatingMode and Valve."""
    __tablename__ = "operating_mode_valve_state"

    mode_id: Mapped[str] = mapped_column(ForeignKey("operating_mode.mode_id"), primary_key=True)
    valve_id: Mapped[str] = mapped_column(ForeignKey("valve.valve_id"), primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False)
    position_pct: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("state IN ('OPEN','CLOSED','THROTTLED')", name="ck_omvs_state"),
        CheckConstraint("position_pct >= 0 AND position_pct <= 100", name="ck_omvs_position"),
    )


class Telemetry(Base):
    __tablename__ = "telemetry"

    telemetry_id: Mapped[str] = mapped_column(String, primary_key=True)
    sensor_id: Mapped[str] = mapped_column(ForeignKey("sensor.sensor_id"), nullable=False)
    ts_utc: Mapped[str] = mapped_column(DateTime, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("quality IN ('GOOD','SUSPECT','BAD')", name="ck_telemetry_quality"),
        UniqueConstraint("sensor_id", "ts_utc", name="uq_telemetry_sensor_ts"),
        Index("ix_telemetry_ts", "ts_utc"),
    )


class Alarm(Base):
    __tablename__ = "alarm"

    alarm_id: Mapped[str] = mapped_column(String, primary_key=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facility.facility_id"), nullable=False)
    sensor_id: Mapped[str | None] = mapped_column(ForeignKey("sensor.sensor_id"), nullable=True)
    alarm_type: Mapped[str] = mapped_column(String, nullable=False)
    raised_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    cleared_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    state: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "alarm_type IN ('LEAK','BLOCKAGE','PUMP_DEGRADATION','SENSOR_FAULT','MASS_BALANCE','OVERFLOW')",
            name="ck_alarm_type"),
        CheckConstraint("state IN ('RAISED','ACKNOWLEDGED','CLEARED')", name="ck_alarm_state"),
        CheckConstraint("cleared_at IS NULL OR raised_at < cleared_at", name="ck_alarm_dates"),
        CheckConstraint("(state = 'CLEARED') = (cleared_at IS NOT NULL)", name="ck_alarm_lifecycle"),
        Index("ix_alarm_facility", "facility_id"),
    )


class SimulationRun(Base):
    __tablename__ = "simulation_run"

    simulation_id: Mapped[str] = mapped_column(String, primary_key=True)
    mode_id: Mapped[str] = mapped_column(ForeignKey("operating_mode.mode_id"), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    assumptions_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('COMPLETED','FAILED')", name="ck_sim_status"),
        CheckConstraint("json_valid(assumptions_json) AND json_valid(result_json)", name="ck_sim_json"),
    )


class SimulationRunAlarm(Base):
    """Bridge table (N:M) between SimulationRun and Alarm."""
    __tablename__ = "simulation_run_alarm"

    simulation_id: Mapped[str] = mapped_column(ForeignKey("simulation_run.simulation_id"), primary_key=True)
    alarm_id: Mapped[str] = mapped_column(ForeignKey("alarm.alarm_id"), primary_key=True)


class ValveStateEvent(Base):
    __tablename__ = "valve_state_event"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    valve_id: Mapped[str] = mapped_column(ForeignKey("valve.valve_id"), nullable=False)
    old_state: Mapped[str] = mapped_column(String, nullable=False)
    new_state: Mapped[str] = mapped_column(String, nullable=False)
    changed_at: Mapped[str] = mapped_column(DateTime, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("old_state IN ('OPEN','CLOSED','THROTTLED')", name="ck_vse_old"),
        CheckConstraint("new_state IN ('OPEN','CLOSED','THROTTLED')", name="ck_vse_new"),
        CheckConstraint("old_state <> new_state", name="ck_vse_changed"),
        Index("ix_vse_valve", "valve_id", "changed_at"),
    )


class EquipmentStatusEvent(Base):
    __tablename__ = "equipment_status_event"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    component_type: Mapped[str] = mapped_column(String, nullable=False)
    component_id: Mapped[str] = mapped_column(String, nullable=False)
    old_status: Mapped[str] = mapped_column(String, nullable=False)
    new_status: Mapped[str] = mapped_column(String, nullable=False)
    changed_at: Mapped[str] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("component_type IN ('PUMP','TANK','FACILITY')", name="ck_ese_type"),
        CheckConstraint("old_status <> new_status", name="ck_ese_changed"),
        Index("ix_ese_component", "component_id", "changed_at"),
    )


class AlarmEvent(Base):
    __tablename__ = "alarm_event"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alarm_id: Mapped[str] = mapped_column(ForeignKey("alarm.alarm_id"), nullable=False)
    old_state: Mapped[str | None] = mapped_column(String, nullable=True)
    new_state: Mapped[str] = mapped_column(String, nullable=False)
    changed_at: Mapped[str] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint("new_state IN ('RAISED','ACKNOWLEDGED','CLEARED')", name="ck_ae_new"),
        Index("ix_ae_alarm", "alarm_id", "changed_at"),
    )