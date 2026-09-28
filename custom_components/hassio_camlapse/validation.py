"""Numeric configuration shared by the UI and entry setup."""

from collections.abc import Mapping
from math import isfinite
from typing import Any

import voluptuous as vol

from .const import (
    CONF_IMAGE_RETENTION_DAYS,
    CONF_INTERVAL_SECONDS,
    CONF_OUTPUT_FPS,
    CONF_VIDEO_RETENTION_DAYS,
    CONF_VIDEOS_PER_DAY,
    DEFAULT_IMAGE_RETENTION_DAYS,
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_OUTPUT_FPS,
    DEFAULT_VIDEO_RETENTION_DAYS,
    DEFAULT_VIDEOS_PER_DAY,
)

# Minimum, maximum, default, display unit.
NUMERIC_FIELDS: dict[str, tuple[int, int, int, str | None]] = {
    CONF_INTERVAL_SECONDS: (1, 3600, DEFAULT_INTERVAL_SECONDS, "s"),
    CONF_OUTPUT_FPS: (1, 60, DEFAULT_OUTPUT_FPS, "fps"),
    CONF_IMAGE_RETENTION_DAYS: (1, 3650, DEFAULT_IMAGE_RETENTION_DAYS, "d"),
    CONF_VIDEO_RETENTION_DAYS: (1, 3650, DEFAULT_VIDEO_RETENTION_DAYS, "d"),
    CONF_VIDEOS_PER_DAY: (1, 24, DEFAULT_VIDEOS_PER_DAY, None),
}


def validate_numeric_config(data: Mapping[str, Any]) -> dict[str, Any]:
    """Reject fractions, booleans and non-finite values; normalize UI floats."""
    result = dict(data)
    for key, (minimum, maximum, default, _) in NUMERIC_FIELDS.items():
        value = result.get(key, default)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not minimum <= value <= maximum
            or not isfinite(value)
            or int(value) != value
        ):
            raise vol.Invalid(f"Must be a whole number between {minimum} and {maximum}", path=[key])
        result[key] = int(value)
    return result
