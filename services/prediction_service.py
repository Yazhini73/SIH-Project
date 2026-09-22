"""Independent model loading and prediction for pH, ammonia, and protein."""

from __future__ import annotations

from pathlib import Path

import joblib

from image_processing.features import feature_vector
from services.ph_calibration import calibrate_ph
from services.ammonia_calibration import calibrate_ammonia
from services.protein_calibration import calibrate_protein


class ModelUnavailableError(RuntimeError):
    pass


class PredictionError(RuntimeError):
    pass


class PredictionService:
    def __init__(self, models_dir: str | Path):
        self.models_dir = Path(models_dir)
        self.model_paths = {
            "ph": self.models_dir / "ph_model.pkl",
            "ammonia": self.models_dir / "ammonia_model.pkl",
            "protein": self.models_dir / "protein_model.pkl",
        }

    def predict(self, parameter: str, chamber) -> float:
        if parameter == "ph" and isinstance(chamber, tuple):
            reference_file = self.models_dir.parent / "dataset" / "ph" / "ph_reference.csv"
            if not reference_file.exists():
                raise ModelUnavailableError("pH reference calibration data is not available.")
            import csv

            with reference_file.open(newline="", encoding="utf-8") as handle:
                return float(calibrate_ph(chamber[0], chamber[1], csv.DictReader(handle)))
        if parameter == "ammonia":
            reference_file = self.models_dir.parent / "dataset" / "ammonia" / "ammonia_reference.csv"
            if not self.model_paths[parameter].exists() and reference_file.exists():
                import csv

                with reference_file.open(newline="", encoding="utf-8") as handle:
                    return float(calibrate_ammonia(chamber, csv.DictReader(handle)))
        if parameter == "protein":
            reference_file = self.models_dir.parent / "dataset" / "protein" / "protein_reference.csv"
            if not self.model_paths[parameter].exists() and reference_file.exists():
                import csv

                with reference_file.open(newline="", encoding="utf-8") as handle:
                    return float(calibrate_protein(chamber, csv.DictReader(handle)))
        path = self.model_paths.get(parameter)
        if path is None or not path.exists():
            label = {"ph": "pH", "ammonia": "Ammonia", "protein": "Protein"}.get(parameter, parameter)
            raise ModelUnavailableError(
                f"{label} model is not trained yet. Add labeled {label.lower()} images and run its training script."
            )
        try:
            model = joblib.load(path)
            value = model.predict(feature_vector(chamber))[0]
            return float(value)
        except Exception as exc:
            raise PredictionError(f"{parameter} prediction failed.") from exc
