from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Facility(Base):
    __tablename__ = "facility"

    facility_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    commissioned_on: Mapped[str] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE','MAINTENANCE','DECOMMISSIONED')", name="ck_facility_status"),
        CheckConstraint("length(trim(name)) > 0", name="ck_facility_name"),
    )


class Pump(Base):
    __tablename__ = "pump"

    pump_id: Mapped[str] = mapped_column(String, primary_key=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facility.facility_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    rated_flow_m3h: Mapped[float] = mapped_column(Float, nullable=False)
    shutoff_head_m: Mapped[float] = mapped_column(Float, nullable=False)
    curve_coeff_k: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    effective_from: Mapped[str] = mapped_column(Date, nullable=False)
    effective_to: Mapped[str | None] = mapped_column(Date, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('RUNNING','STANDBY','FAULTED','MAINTENANCE')", name="ck_pump_status"),
        CheckConstraint("rated_flow_m3h > 0", name="ck_pump_rated_flow"),
        CheckConstraint("shutoff_head_m > 0", name="ck_pump_head"),
        CheckConstraint("curve_coeff_k > 0", name="ck_pump_k"),
        CheckConstraint("effective_to IS NULL OR effective_from <= effective_to", name="ck_pump_dates"),
        Index("ix_pump_facility", "facility_id"),
    )


class Tank(Base):
    __tablename__ = "tank"

    tank_id: Mapped[str] = mapped_column(String, primary_key=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facility.facility_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    capacity_m3: Mapped[float] = mapped_column(Float, nullable=False)
    cross_section_m2: Mapped[float] = mapped_column(Float, nullable=False)
    min_level_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_level_pct: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('IN_SERVICE','OUT_OF_SERVICE')", name="ck_tank_status"),
        CheckConstraint("capacity_m3 > 0", name="ck_tank_capacity"),
        CheckConstraint("cross_section_m2 > 0", name="ck_tank_area"),
        CheckConstraint("min_level_pct >= 0 AND min_level_pct < max_level_pct AND max_level_pct <= 100", name="ck_tank_levels"),
        Index("ix_tank_facility", "facility_id"),
    )


class Valve(Base):
    __tablename__ = "valve"

    valve_id: Mapped[str] = mapped_column(String, primary_key=True)
    facility_id: Mapped[str] = mapped_column(ForeignKey("facility.facility_id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    default_state: Mapped[str] = mapped_column(String, nullable=False)
    default_position_pct: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("default_state IN ('OPEN','CLOSED','THROTTLED')", name="ck_valve_state"),
        CheckConstraint("default_position_pct >= 0 AND default_position_pct <= 100", name="ck_valve_position"),
        Index("ix_valve_facility", "facility_id"),
    )