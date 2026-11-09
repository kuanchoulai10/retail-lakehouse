"""Define the MeasurementUnit enumeration."""

from __future__ import annotations

from enum import StrEnum


class MeasurementUnit(StrEnum):
    """Enumerate the units a measurement is counted in."""

    COUNT = "count"
    BYTES = "bytes"
    SECONDS = "seconds"
