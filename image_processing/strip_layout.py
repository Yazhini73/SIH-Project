"""Rounded six-chamber strip validation and cropping."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np


CHAMBER_NAMES = ("ph_acid", "ph_alkaline", "protein", "control", "ammonia", "moisture")
DEFAULT_ERROR = (
    "Unable to identify all test chambers. Please place the complete test strip "
    "inside the scanning area and capture again."
)
LOGGER = logging.getLogger(__name__)
LAST_DETECTION_DEBUG: dict[str, Any] = {}


class StripLayoutError(ValueError):
    """Raised when a complete, usable strip cannot be extracted."""

    def __init__(self, message: str = DEFAULT_ERROR):
        super().__init__(message)


def get_last_detection_debug() -> dict[str, Any]:
    """Return the latest non-image debug metadata for development diagnostics."""
    return dict(LAST_DETECTION_DEBUG)


def _load_image(image: bytes | np.ndarray) -> np.ndarray:
    if isinstance(image, bytes):
        decoded = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
    else:
        decoded = image
    if decoded is None or decoded.size == 0:
        raise StripLayoutError("The uploaded image could not be read. Please choose a valid image.")
    if decoded.ndim != 3 or decoded.shape[2] != 3:
        raise StripLayoutError("Please upload a color image of the complete test strip.")
    return decoded


def _relative_box(box: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int]:
    x = int(round(float(box["x"]) * width))
    y = int(round(float(box["y"]) * height))
    w = int(round(float(box["width"]) * width))
    h = int(round(float(box["height"]) * height))
    if min(x, y, w, h) < 0 or w < 4 or h < 4 or x + w > width or y + h > height:
        raise StripLayoutError()
    return x, y, w, h


def _configured_box(box: dict[str, Any]) -> bool:
    return all(box.get(key) is not None for key in ("x", "y", "width", "height"))


def _candidate_masks(image: np.ndarray) -> list[np.ndarray]:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    normalized = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(lab[:, :, 0])
    blurred = cv2.GaussianBlur(normalized, (5, 5), 0)
    masks = [cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]]
    masks.append(cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5))
    edges = cv2.Canny(blurred, 40, 140)
    masks.append(cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17))))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    return [cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel) for mask in masks]


def _find_strip(image: np.ndarray, config: dict[str, Any]) -> np.ndarray:
    """Return a normalized crop without assuming an elongated rectangle."""
    height, width = image.shape[:2]
    configured_frame = config.get("strip_frame") or {}
    if _configured_box(configured_frame):
        x, y, w, h = _relative_box(configured_frame, width, height)
        return image[y : y + h, x : x + w].copy()

    image_area = height * width
    detection = config.get("strip_detection", {})
    minimum = float(detection.get("min_area_ratio", 0.05)) * image_area
    maximum = float(detection.get("max_area_ratio", 0.95)) * image_area
    candidates: list[tuple[float, np.ndarray]] = []
    for mask in _candidate_masks(image):
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if not minimum <= area <= maximum:
                continue
            rect = cv2.minAreaRect(contour)
            rw, rh = rect[1]
            if min(rw, rh) < 20:
                continue
            box = cv2.boxPoints(rect).astype(np.float32)
            perimeter = cv2.arcLength(contour, True)
            compactness = (4.0 * np.pi * area / (perimeter * perimeter)) if perimeter else 0.0
            ratio = max(rw, rh) / min(rw, rh)
            # Circular/rounded boards score well; elongated objects are still
            # accepted, but no longer receive an artificial aspect-ratio bonus.
            shape_score = 0.65 + min(compactness, 1.0) * 0.35
            ratio_penalty = 1.0 / (1.0 + max(ratio - 3.0, 0.0) * 0.15)
            candidates.append((area * shape_score * ratio_penalty, box))
    if not candidates:
        raise StripLayoutError("Unable to identify the rounded strip region.")

    _, box = max(candidates, key=lambda item: item[0])
    ordered = _order_box_points(box)
    top_left, top_right, bottom_right, bottom_left = ordered
    out_width = max(int(np.linalg.norm(top_right - top_left)), int(np.linalg.norm(bottom_right - bottom_left)))
    out_height = max(int(np.linalg.norm(bottom_left - top_left)), int(np.linalg.norm(bottom_right - top_right)))
    if min(out_width, out_height) < 40:
        raise StripLayoutError("Detected strip region is too small for six chamber crops.")
    destination = np.array([[0, 0], [out_width - 1, 0], [out_width - 1, out_height - 1], [0, out_height - 1]], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(ordered, destination)
    return cv2.warpPerspective(image, transform, (out_width, out_height))


def _order_box_points(points: np.ndarray) -> np.ndarray:
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).ravel()
    return np.array([points[np.argmin(sums)], points[np.argmin(differences)], points[np.argmax(sums)], points[np.argmax(differences)]], dtype=np.float32)


def _derive_chambers(strip: np.ndarray, config: dict[str, Any]) -> dict[str, np.ndarray]:
    height, width = strip.shape[:2]
    chamber_config = config.get("chambers", {})
    if all(_configured_box(chamber_config.get(name, {})) for name in CHAMBER_NAMES):
        return {name: strip[y : y + h, x : x + w].copy() for name in CHAMBER_NAMES for x, y, w, h in [_relative_box(chamber_config[name], width, height)]}

    # The real board is a rounded/circular layout, not a six-slot strip.
    # Coordinates are normalized so rotation/perspective normalization above
    # does not make chamber identity depend on color or contour perfection.
    layout = config.get("layout", {})
    positions = layout.get("circular_positions") or {
        "ph_acid": (0.34, 0.27),
        "ph_alkaline": (0.66, 0.27),
        "protein": (0.28, 0.50),
        "control": (0.72, 0.50),
        "ammonia": (0.36, 0.73),
        "moisture": (0.64, 0.73),
    }
    crop_ratio = float(layout.get("circular_crop_ratio", 0.23))
    crop_width = max(8, int(width * crop_ratio))
    crop_height = max(8, int(height * crop_ratio))
    crops: dict[str, np.ndarray] = {}
    for name in CHAMBER_NAMES:
        center_x, center_y = positions.get(name, (None, None))
        if center_x is None or center_y is None:
            raise StripLayoutError(f"Missing normalized position for {name} chamber.")
        center_x = int(round(float(center_x) * width))
        center_y = int(round(float(center_y) * height))
        left = max(0, center_x - crop_width // 2)
        top = max(0, center_y - crop_height // 2)
        right = min(width, left + crop_width)
        bottom = min(height, top + crop_height)
        crop = strip[top:bottom, left:right]
        if crop.size == 0 or min(crop.shape[:2]) < 4:
            raise StripLayoutError()
        crops[name] = crop.copy()
    return crops


def _validate_crops(crops: dict[str, np.ndarray], config: dict[str, Any]) -> None:
    if set(crops) != set(CHAMBER_NAMES) or any(crop.size == 0 for crop in crops.values()):
        raise StripLayoutError()
    control = crops["control"]
    control_gray = cv2.cvtColor(control, cv2.COLOR_BGR2GRAY)
    minimum_mean = float(config.get("validation", {}).get("minimum_control_mean", 1.0))
    if not np.isfinite(control_gray).all() or float(np.mean(control_gray)) <= minimum_mean:
        raise StripLayoutError("The control chamber is invalid. Please capture the complete strip again.")


def detect_and_crop(image: bytes | np.ndarray, config_path: str | Path) -> dict[str, np.ndarray]:
    """Detect one complete strip and return six position-based chamber crops."""
    global LAST_DETECTION_DEBUG
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    decoded = _load_image(image)
    strip = _find_strip(decoded, config)
    crops = _derive_chambers(strip, config)
    _validate_crops(crops, config)
    LAST_DETECTION_DEBUG = {
        "original_dimensions": {"width": int(decoded.shape[1]), "height": int(decoded.shape[0])},
        "perspective_corrected_dimensions": {"width": int(strip.shape[1]), "height": int(strip.shape[0])},
        "chamber_count": len(crops),
        "chambers": {name: {"width": int(crop.shape[1]), "height": int(crop.shape[0])} for name, crop in crops.items()},
    }
    LOGGER.debug("strip detection: %s", LAST_DETECTION_DEBUG)
    return crops
