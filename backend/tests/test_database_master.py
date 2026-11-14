from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base, make_engine
from app.models import Facility, Pump, Tank, Valve


@pytest.fixture()
def session():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def add_facility(s, fid="FAC-001", name="Plant A"):
    s.add(Facility(facility_id=fid, name=name, status="ACTIVE", commissioned_on=date(2020, 1, 1)))
    s.commit()


def make_pump(**kw):
    base = dict(pump_id="PUMP-001", facility_id="FAC-001", name="P1", rated_flow_m3h=100.0,
                shutoff_head_m=50.0, curve_coeff_k=0.002, status="RUNNING",
                effective_from=date(2024, 1, 1), effective_to=None)
    base.update(kw)
    return Pump(**base)


def test_valid_pump_saves(session):
    add_facility(session)
    session.add(make_pump())
    session.commit()
    assert session.get(Pump, "PUMP-001").rated_flow_m3h == 100.0


def test_duplicate_primary_key_rejected(session):
    add_facility(session)
    with pytest.raises(IntegrityError):
        add_facility(session)


def test_duplicate_facility_name_rejected(session):
    add_facility(session)
    with pytest.raises(IntegrityError):
        add_facility(session, fid="FAC-002", name="Plant A")


def test_pump_with_missing_facility_rejected(session):
    session.add(make_pump(facility_id="FAC-999"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_bad_pump_status_rejected(session):
    add_facility(session)
    session.add(make_pump(status="BROKEN"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_negative_flow_rejected(session):
    add_facility(session)
    session.add(make_pump(rated_flow_m3h=0))
    with pytest.raises(IntegrityError):
        session.commit()


def test_pump_dates_out_of_order_rejected(session):
    add_facility(session)
    session.add(make_pump(effective_to=date(2023, 1, 1)))
    with pytest.raises(IntegrityError):
        session.commit()


def test_tank_level_limits_rejected(session):
    add_facility(session)
    session.add(Tank(tank_id="TANK-001", facility_id="FAC-001", name="T1", capacity_m3=500.0,
                     cross_section_m2=20.0, min_level_pct=90.0, max_level_pct=50.0, status="IN_SERVICE"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_valve_position_over_100_rejected(session):
    add_facility(session)
    session.add(Valve(valve_id="VALVE-001", facility_id="FAC-001", name="V1",
                      default_state="OPEN", default_position_pct=150.0))
    with pytest.raises(IntegrityError):
        session.commit()