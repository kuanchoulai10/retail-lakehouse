"""Define the MeasurementComparison enumeration."""

from __future__ import annotations

from enum import StrEnum


class MeasurementComparison(StrEnum):
    """Enumerate how an observed value is compared with its threshold."""

    AT_LEAST = ">="
    MORE_THAN = ">"
    LESS_THAN = "<"
    AT_MOST = "<="
