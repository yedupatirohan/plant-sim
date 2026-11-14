"""Create the SQLite database and load the seed CSV files into it.

Run from the backend folder:
    python -m app.init_db
"""
import argparse
from pathlib import Path

from app.core.database import Base, make_engine
from app.services.loader import load_seed

# Importing the models registers every table on Base.
import app.models.master  # noqa: F401
import app.models.network  # noqa: F401

# backend/app/init_db.py -> parents[2] is the project root
DEFAULT_SEED_DIR = Path(__file__).resolve().parents[2] / "data" / "seed"


def init_db(seed_dir: Path = DEFAULT_SEED_DIR, reset: bool = True, url: str | None = None) -> dict:
    engine = make_engine(url)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    counts = load_seed(engine, seed_dir)
    engine.dispose()
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create DB and load seed data")
    parser.add_argument("--seed-dir", type=Path, default=DEFAULT_SEED_DIR)
    parser.add_argument("--keep", action="store_true", help="do not drop existing tables first")
    args = parser.parse_args()
    result = init_db(args.seed_dir, reset=not args.keep)
    for table, n in result.items():
        print(f"{table}: {n}")
    print("DATABASE READY")