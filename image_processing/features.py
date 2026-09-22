"""Shared RGB, HSV, and LAB feature extraction for training and prediction."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


FEATURE_NAMES = [
    "mean_r",
    "mean_g",
    "mean_b",
    "mean_h",
    "mean_s",
    "mean_v",
    "mean_l",
    "mean_a",
    "mean_lab_b",
]


def _as_image(image: np.ndarray | str | Path) -> np.ndarray:
    if isinstance(image, (str, Path)):
        loaded = cv2.imread(str(image))
        if loaded is None:
            raise ValueError("Unable to read image.")
        return cv2.cvtColor(loaded, cv2.COLOR_BGR2RGB)
    if image is None or image.size == 0:
        raise ValueError("Image is empty.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("Image must have three color channels.")
    return image


def extract_color_features(image: np.ndarray | str | Path) -> dict[str, float]:
    """Return deterministic mean RGB, HSV, and LAB values."""
    rgb = _as_image(image)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    channels = (*cv2.split(rgb), *cv2.split(hsv), *cv2.split(lab))
    means = [float(np.mean(channel)) for channel in channels]
    return dict(zip(FEATURE_NAMES, means))


def feature_vector(image: np.ndarray | str | Path) -> np.ndarray:
    features = extract_color_features(image)
    return np.asarray([[features[name] for name in FEATURE_NAMES]], dtype=np.float32)
