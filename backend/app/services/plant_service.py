"""Plant data rules: 404 for unknown ids, limits and time checks for telemetry."""
from datetime import datetime, timezone

from app.core.errors import NotFoundError, ValidationFailure
from app.repositories.plant_repo import PlantRepository

MAX_TELEMETRY_LIMIT = 5000


def _naive_utc(ts: datetime | None) -> datetime | None:
    """The database stores UTC without a zone, so compare like with like."""
    if ts is not None and ts.tzinfo is not None:
        return ts.astimezone(timezone.utc).replace(tzinfo=None)
    return ts


class PlantService:
    def __init__(self, repo: PlantRepository):
        self.repo = repo

    def list_facilities(self):
        return self.repo.list_facilities()

    def get_facility(self, facility_id: str):
        facility = self.repo.get_facility(facility_id)
        if facility is None:
            raise NotFoundError(f"Facility {facility_id} not found")
        return facility

    def components(self, facility_id: str) -> dict:
        self.get_facility(facility_id)
        return {
            "facility_id": facility_id,
            "pumps": self.repo.list_pumps(facility_id),
            "tanks": self.repo.list_tanks(facility_id),
            "valves": self.repo.list_valves(facility_id),
            "pipes": self.repo.list_pipes(facility_id),
            "sensors": self.repo.list_sensors(facility_id),
        }

    def modes(self, facility_id: str):
        self.get_facility(facility_id)
        return self.repo.list_modes(facility_id)

    def telemetry(self, sensor_id: str, start: datetime | None = None,
                  end: datetime | None = None, limit: int = 1000) -> dict:
        sensor = self.repo.get_sensor(sensor_id)
        if sensor is None:
            raise NotFoundError(f"Sensor {sensor_id} not found")
        if not 1 <= limit <= MAX_TELEMETRY_LIMIT:
            raise ValidationFailure(f"limit must be between 1 and {MAX_TELEMETRY_LIMIT}")
        start, end = _naive_utc(start), _naive_utc(end)
        if start is not None and end is not None and start > end:
            raise ValidationFailure("start must not be after end")
        rows = self.repo.get_telemetry(sensor_id, start, end, limit)
        points = [{"ts_utc": r.ts_utc, "value": r.value, "quality": r.quality} for r in rows]
        return {"sensor_id": sensor_id, "measurement": sensor.measurement,
                "unit": sensor.unit, "count": len(points), "points": points}