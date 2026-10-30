"""Define the TableMaintenanceSignal names."""

from __future__ import annotations

from enum import StrEnum


class TableMaintenanceSignal(StrEnum):
    """Name the signals a table maintenance workflow receives."""

    OPERATION_RESULT = "operation_result"
    ADMISSION_GRANTED = "admission_granted"
