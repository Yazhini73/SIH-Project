"""Reference-backed ammonia calibration for tables without paired images."""

from __future__ import annotations

import re
from typing import Iterable

import cv2
import numpy as np

from services.ph_calibration import _reference_rgb


def _normalized_rgb(chamber: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(chamber, cv2.COLOR_BGR2RGB).reshape(-1, 3).astype(np.float32)
    rgb = np.median(rgb, axis=0)
    return rgb / max(float(rgb.sum()), 1.0)


def calibrate_ammonia(chamber: np.ndarray, rows: Iterable[dict[str, str]]) -> float:
    """Return the ppm from the nearest existing Color reference row."""
    observed = _normalized_rgb(chamber)
    candidates = []
    for row in rows:
        try:
            value = float(row["Ammonia (ppm)"])
            reference = _reference_rgb(row["Color"])
            reference = reference / max(float(reference.sum()), 1.0)
            candidates.append((float(np.linalg.norm(observed - reference)), value))
        except (KeyError, TypeError, ValueError):
            continue
    if not candidates:
        raise ValueError("The ammonia reference table has no usable calibration rows.")
    return min(candidates, key=lambda item: item[0])[1]
