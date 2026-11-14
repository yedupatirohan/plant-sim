"""Reads the labelled ground truth file. Read-only. No business rules here."""
import csv
from pathlib import Path

from app.core.errors import NotFoundError

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "ground_truth" / "ground_truth.csv"


class GroundTruthRepository:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)

    def load(self) -> list[dict]:
        if not self.path.is_file():
            raise NotFoundError(f"Ground truth file not found: {self.path.name}")
        with self.path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))