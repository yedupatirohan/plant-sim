from datetime import date, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base, make_engine
from app.models import (Alarm, Facility, OperatingMode, Pipe, Sensor, SimulationRun,
                        Telemetry, Valve, ValveStateEvent)

T0 = datetime(2026, 1, 1, 0, 0, 0)
T1 = datetime(2026, 1, 1, 1, 0, 0)


@pytest.fixture()
def s():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Facility(facility_id="FAC-001", name="A", status="ACTIVE", commissioned_on=date(2020, 1, 1)))
        session.add(Valve(valve_id="VALVE-001", facility_id="FAC-001", name="V", default_state="OPEN",
                          default_position_pct=100.0))
        session.add(OperatingMode(mode_id="MODE-001", facility_id="FAC-001", name="NORMAL",
                                  pump_speed_pct=80.0, effective_from=T0))
        session.add(Sensor(sensor_id="SNS-001", facility_id="FAC-001", component_type="PIPE",
                           component_id="PIPE-001", measurement="FLOW", unit="m3/h"))
        session.commit()
        yield session


def test_pipe_same_node_rejected(s):
    s.add(Pipe(pipe_id="PIPE-001", facility_id="FAC-001", from_node_id="TANK-001",
               to_node_id="TANK-001", length_m=10, diameter_mm=100))
    with pytest.raises(IntegrityError):
        s.commit()


def test_sensor_unit_must_match_measurement(s):
    s.add(Sensor(sensor_id="SNS-002", facility_id="FAC-001", component_type="PIPE",
                 component_id="PIPE-001", measurement="FLOW", unit="kPa"))
    with pytest.raises(IntegrityError):
        s.commit()


def test_duplicate_telemetry_sensor_timestamp_rejected(s):
    s.add(Telemetry(telemetry_id="TEL-000001", sensor_id="SNS-001", ts_utc=T0, value=5.0, quality="GOOD"))
    s.commit()
    s.add(Telemetry(telemetry_id="TEL-000002", sensor_id="SNS-001", ts_utc=T0, value=6.0, quality="GOOD"))
    with pytest.raises(IntegrityError):
        s.commit()


def test_telemetry_unknown_sensor_rejected(s):
    s.add(Telemetry(telemetry_id="TEL-000001", sensor_id="SNS-999", ts_utc=T0, value=5.0, quality="GOOD"))
    with pytest.raises(IntegrityError):
        s.commit()


def test_simulation_without_input_configuration_rejected(s):
    s.add(SimulationRun(simulation_id="SIM-2026-000001", mode_id="MODE-999", seed=1,
                        assumptions_json="{}", result_json="{}", status="COMPLETED"))
    with pytest.raises(IntegrityError):
        s.commit()


def test_simulation_invalid_json_rejected(s):
    s.add(SimulationRun(simulation_id="SIM-2026-000001", mode_id="MODE-001", seed=1,
                        assumptions_json="not json", result_json="{}", status="COMPLETED"))
    with pytest.raises(IntegrityError):
        s.commit()


def test_alarm_cleared_state_needs_cleared_time(s):
    s.add(Alarm(alarm_id="ALM-000001", facility_id="FAC-001", sensor_id="SNS-001", alarm_type="LEAK",
                raised_at=T0, cleared_at=None, state="CLEARED"))
    with pytest.raises(IntegrityError):
        s.commit()


def test_alarm_dates_out_of_order_rejected(s):
    s.add(Alarm(alarm_id="ALM-000001", facility_id="FAC-001", sensor_id="SNS-001", alarm_type="LEAK",
                raised_at=T1, cleared_at=T0, state="CLEARED"))
    with pytest.raises(IntegrityError):
        s.commit()


def test_valve_event_must_change_state(s):
    s.add(ValveStateEvent(valve_id="VALVE-001", old_state="OPEN", new_state="OPEN",
                          changed_at=T0, reason="test"))
    with pytest.raises(IntegrityError):
        s.commit()


def test_valid_alarm_saves(s):
    s.add(Alarm(alarm_id="ALM-000001", facility_id="FAC-001", sensor_id="SNS-001", alarm_type="LEAK",
                raised_at=T0, cleared_at=T1, state="CLEARED"))
    s.commit()
    assert s.get(Alarm, "ALM-000001").state == "CLEARED"