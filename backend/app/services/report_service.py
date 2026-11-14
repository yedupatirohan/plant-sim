"""Services that combine other services: detect-and-raise, and the data-quality report."""
from app.models.master import Facility, Pump, Tank, Valve
from app.models.network import Alarm, OperatingMode, Pipe, Sensor, SimulationRun, Telemetry
from app.repositories.plant_repo import PlantRepository
from app.services.alarm_service import AlarmService
from app.services.balance_service import BalanceService
from app.services.detection_service import DetectionService
from app.services.topology_service import TopologyService

COUNTED = {
    "facilities": Facility, "pumps": Pump, "tanks": Tank, "valves": Valve,
    "pipes": Pipe, "sensors": Sensor, "operating_modes": OperatingMode,
    "telemetry": Telemetry, "alarms": Alarm, "simulation_runs": SimulationRun,
}


class DetectAndRaiseService:
    def __init__(self, detection: DetectionService, alarms: AlarmService):
        self.detection = detection
        self.alarms = alarms

    def run(self, facility_id: str | None = None) -> dict:
        events = self.detection.detect(facility_id)
        created = self.alarms.raise_from_events(events)
        return {"events_found": len(events), "alarms_created": len(created),
                "alarms": created}


class DataQualityService:
    def __init__(self, repo: PlantRepository, topology: TopologyService,
                 balance: BalanceService):
        self.repo = repo
        self.topology = topology
        self.balance = balance

    def report(self) -> dict:
        topology = self.topology.check_all()
        balance = self.balance.check_all()
        first, last = self.repo.telemetry_time_range()
        issues = (any(t["status"] != "OK" for t in topology)
                  or any(b["status"] == "VIOLATIONS" for b in balance))
        return {
            "overall": "ISSUES" if issues else "OK",
            "counts": {name: self.repo.count(model) for name, model in COUNTED.items()},
            "telemetry_from": first,
            "telemetry_to": last,
            "topology": topology,
            "balance": balance,
        }