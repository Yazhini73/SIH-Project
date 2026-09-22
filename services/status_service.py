"""Centralized three-status evaluation using config/status_ranges.json."""

from __future__ import annotations

import json
from pathlib import Path


class StatusConfigurationError(RuntimeError):
    pass


class StatusService:
    def __init__(self, config_path: str | Path):
        self.config = json.loads(Path(config_path).read_text(encoding="utf-8"))

    def status(self, parameter: str, value: float) -> str:
        ranges = self.config.get(parameter, {})
        for status in ("GOOD", "MODERATE", "BAD"):
            rule = ranges.get(status.lower())
            if isinstance(rule, dict):
                rule = [rule]
            if not rule:
                continue
            for interval in rule:
                if interval.get("min") is None or interval.get("max") is None:
                    continue
                if float(interval["min"]) <= value <= float(interval["max"]):
                    return status
        raise StatusConfigurationError(f"{parameter.capitalize()} status ranges are not configured.")

    def details(self, parameter: str, status: str) -> dict[str, str]:
        details = self.config.get(parameter, {}).get("details", {}).get(status, {})
        return {key: str(details.get(key, "")) for key in ("condition", "problem", "remedy")}

    @staticmethod
    def color(status: str) -> str:
        return {"GOOD": "green", "MODERATE": "yellow", "BAD": "red"}[status]
