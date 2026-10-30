"""Define the TableMaintenanceAdmissionSignal names."""

from __future__ import annotations

from enum import StrEnum


class TableMaintenanceAdmissionSignal(StrEnum):
    """Name the signals the table maintenance admission workflow receives."""

    ACQUIRE = "acquire"
    RELEASE = "release"
