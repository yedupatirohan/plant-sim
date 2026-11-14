"""Read-only database queries for plant data. No business rules here."""
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.master import Facility, Pump, Tank, Valve
from app.models.network import (
    Pipe, Sensor, OperatingMode, OperatingModeValveState, Telemetry,
)


class PlantRepository:
    def __init__(self, session: Session):
        self.session = session

    # ---------- helpers ----------
    def _list(self, model, facility_id: str | None, order_col):
        stmt = select(model).order_by(order_col)
        if facility_id:
            stmt = stmt.where(model.facility_id == facility_id)
        return list(self.session.scalars(stmt))

    # ---------- facilities and components ----------
    def list_facilities(self) -> list[Facility]:
        return list(self.session.scalars(select(Facility).order_by(Facility.facility_id)))

    def get_facility(self, facility_id: str) -> Facility | None:
        return self.session.get(Facility, facility_id)

    def list_pumps(self, facility_id: str | None = None) -> list[Pump]:
        return self._list(Pump, facility_id, Pump.pump_id)

    def list_tanks(self, facility_id: str | None = None) -> list[Tank]:
        return self._list(Tank, facility_id, Tank.tank_id)

    def list_valves(self, facility_id: str | None = None) -> list[Valve]:
        return self._list(Valve, facility_id, Valve.valve_id)

    def list_pipes(self, facility_id: str | None = None) -> list[Pipe]:
        return self._list(Pipe, facility_id, Pipe.pipe_id)

    def list_sensors(self, facility_id: str | None = None) -> list[Sensor]:
        return self._list(Sensor, facility_id, Sensor.sensor_id)

    def get_pump(self, pump_id: str) -> Pump | None:
        return self.session.get(Pump, pump_id)

    def get_sensor(self, sensor_id: str) -> Sensor | None:
        return self.session.get(Sensor, sensor_id)

    # ---------- operating modes ----------
    def list_modes(self, facility_id: str | None = None) -> list[OperatingMode]:
        return self._list(OperatingMode, facility_id, OperatingMode.mode_id)

    def get_mode(self, mode_id: str) -> OperatingMode | None:
        return self.session.get(OperatingMode, mode_id)

    def get_mode_valve_states(self, mode_id: str) -> list[OperatingModeValveState]:
        stmt = (
            select(OperatingModeValveState)
            .where(OperatingModeValveState.mode_id == mode_id)
            .order_by(OperatingModeValveState.valve_id)
        )
        return list(self.session.scalars(stmt))

    # ---------- telemetry ----------
    def get_telemetry(
        self,
        sensor_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 1000,
    ) -> list[Telemetry]:
        stmt = select(Telemetry).where(Telemetry.sensor_id == sensor_id)
        if start is not None:
            stmt = stmt.where(Telemetry.ts_utc >= start)
        if end is not None:
            stmt = stmt.where(Telemetry.ts_utc <= end)
        stmt = stmt.order_by(Telemetry.ts_utc).limit(limit)
        return list(self.session.scalars(stmt))

    def get_telemetry_for_sensors(
        self, sensor_ids: list[str], start: datetime | None = None, end: datetime | None = None
    ) -> list[Telemetry]:
        """All rows for many sensors, ordered by time. Used by detection."""
        if not sensor_ids:
            return []
        stmt = select(Telemetry).where(Telemetry.sensor_id.in_(sensor_ids))
        if start is not None:
            stmt = stmt.where(Telemetry.ts_utc >= start)
        if end is not None:
            stmt = stmt.where(Telemetry.ts_utc <= end)
        stmt = stmt.order_by(Telemetry.sensor_id, Telemetry.ts_utc)
        return list(self.session.scalars(stmt))

    def telemetry_time_range(self) -> tuple[datetime | None, datetime | None]:
        row = self.session.execute(
            select(func.min(Telemetry.ts_utc), func.max(Telemetry.ts_utc))
        ).one()
        return row[0], row[1]

    # ---------- counts (for data-quality page) ----------
    def count(self, model) -> int:
        return self.session.scalar(select(func.count()).select_from(model)) or 0