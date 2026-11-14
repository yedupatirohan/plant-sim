"""Load generated CSV seed data into the database in one transaction."""
import csv
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import insert
from sqlalchemy.engine import Engine

from app.core.database import Base
from app.models import (Facility, OperatingMode, OperatingModeValveState, Pipe, Pump,
                        Sensor, Tank, Telemetry, Valve)

# Parent tables first, then children.
LOAD_ORDER = [
    ("facility", Facility), ("pump", Pump), ("tank", Tank), ("valve", Valve),
    ("pipe", Pipe), ("sensor", Sensor), ("operating_mode", OperatingMode),
    ("operating_mode_valve_state", OperatingModeValveState), ("telemetry", Telemetry),
]

DATE_COLS = {"commissioned_on", "effective_from_date"}
FLOAT_COLS = {"capacity_m3", "cross_section_m2", "min_level_pct", "max_level_pct", "rated_flow_m3h",
              "shutoff_head_m", "curve_coeff_k", "default_position_pct", "length_m", "diameter_mm",
              "pump_speed_pct", "position_pct", "value"}


def _convert(model, row: dict) -> dict:
    out = {}
    cols = {c.name: c for c in model.__table__.columns}
    for k, v in row.items():
        col = cols[k]
        if v == "":
            out[k] = None
        elif k in FLOAT_COLS:
            out[k] = float(v)
        elif type(col.type).__name__ == "Date":
            out[k] = date.fromisoformat(v)
        elif type(col.type).__name__ == "DateTime":
            out[k] = datetime.fromisoformat(v)
        else:
            out[k] = v
    return out


def load_seed(engine: Engine, seed_dir: Path, batch: int = 5000) -> dict:
    seed_dir = Path(seed_dir)
    Base.metadata.create_all(engine)
    counts = {}
    with engine.begin() as conn:  # one transaction: all or nothing
        for name, model in LOAD_ORDER:
            with open(seed_dir / f"{name}.csv", encoding="utf-8", newline="") as f:
                rows = [_convert(model, r) for r in csv.DictReader(f)]
            for i in range(0, len(rows), batch):
                conn.execute(insert(model), rows[i:i + batch])
            counts[name] = len(rows)
    return counts
