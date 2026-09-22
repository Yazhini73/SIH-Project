"""Reference CSV loading without modifying or fabricating reference values."""

from __future__ import annotations

import csv
from pathlib import Path


class ReferenceDataError(RuntimeError):
    pass


class ReferenceService:
    def __init__(self, dataset_dir: str | Path):
        self.dataset_dir = Path(dataset_dir)
        self.files = {
            "ph": self.dataset_dir / "ph" / "ph_reference.csv",
            "ammonia": self.dataset_dir / "ammonia" / "ammonia_reference.csv",
            "protein": self.dataset_dir / "protein" / "protein_reference.csv",
        }

    def rows(self, parameter: str) -> list[dict[str, str]]:
        path = self.files.get(parameter)
        if path is None or not path.exists():
            raise ReferenceDataError(f"{parameter.capitalize()} reference data is not available yet.")
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise ReferenceDataError(f"{parameter.capitalize()} reference data is empty.")
        return rows

    def pH_rows(self) -> list[dict[str, str]]:
        return self.rows("ph")

    def nearest(self, parameter: str, value: float) -> dict[str, str]:
        rows = self.rows(parameter)
        value_key = {"ph": "pH", "ammonia": "Ammonia (ppm)", "protein": "Protein (%)"}[parameter]
        usable = []
        for row in rows:
            try:
                usable.append((abs(float(row[value_key]) - value), row))
            except (KeyError, TypeError, ValueError):
                continue
        if not usable:
            raise ReferenceDataError(f"{parameter.capitalize()} reference data has no usable numeric values.")
        return min(usable, key=lambda item: item[0])[1]
