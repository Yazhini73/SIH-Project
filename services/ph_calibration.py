"""Reference-backed pH calibration for tables without paired chamber images.

This is not an image-trained model. It uses the existing Color/pH reference
rows and normalized chamber color features to select the nearest calibration
row, then returns that row's existing numeric pH value.
"""

from __future__ import annotations

import re
from typing import Iterable

import cv2
import numpy as np


_BASE_COLORS = {
    "red": np.array([190.0, 45.0, 45.0]),
    "orange": np.array([220.0, 125.0, 35.0]),
    "yellow": np.array([220.0, 205.0, 45.0]),
    "green": np.array([50.0, 155.0, 70.0]),
    "blue": np.array([55.0, 115.0, 195.0]),
    "violet": np.array([105.0, 55.0, 150.0]),
    "purple": np.array([115.0, 55.0, 145.0]),
}


def _reference_rgb(description: str) -> np.ndarray:
    words = set(re.findall(r"[a-z]+", description.lower()))
    selected = next((color for color in _BASE_COLORS if color in words), None)
    color = _BASE_COLORS.get(selected, np.array([128.0, 128.0, 128.0])).copy()
    if "dark" in words:
        color *= 0.58
    elif "light" in words:
        color = color * 0.72 + 255.0 * 0.28
    elif "pale" in words or "very" in words:
        color = color * 0.45 + 255.0 * 0.55
    if "blue" in words and selected not in {"blue", "violet", "purple"}:
        color = color * 0.65 + np.array([40.0, 100.0, 190.0]) * 0.35
    if "green" in words and selected not in {"green"}:
        color = color * 0.65 + np.array([55.0, 155.0, 70.0]) * 0.35
    if "red" in words and selected not in {"red"}:
        color = color * 0.65 + np.array([190.0, 45.0, 45.0]) * 0.35
    return np.clip(color, 0, 255)


def _normalized_rgb(chamber: np.ndarray) -> np.ndarray:
    rgb = cv2.cvtColor(chamber, cv2.COLOR_BGR2RGB).reshape(-1, 3).astype(np.float32)
    rgb = np.median(rgb, axis=0)
    total = max(float(rgb.sum()), 1.0)
    return rgb / total


def calibrate_ph(ph_acid: np.ndarray, ph_alkaline: np.ndarray, rows: Iterable[dict[str, str]]) -> float:
    """Select the nearest existing reference row using both pH chambers."""
    observed = np.mean([_normalized_rgb(ph_acid), _normalized_rgb(ph_alkaline)], axis=0)
    candidates = []
    for row in rows:
        try:
            reference_value = float(row["pH"])
            reference = _reference_rgb(row["Color"])
            reference = reference / max(float(reference.sum()), 1.0)
            candidates.append((float(np.linalg.norm(observed - reference)), reference_value))
        except (KeyError, TypeError, ValueError):
            continue
    if not candidates:
        raise ValueError("The pH reference table has no usable calibration rows.")
    return min(candidates, key=lambda item: item[0])[1]
