"""Define the OperationResult enumeration."""

from __future__ import annotations

from enum import StrEnum


class OperationResult(StrEnum):
    """Enumerate what a reconciliation did about one operation."""

    STARTED = "started"
    WOULD_START = "would_start"
    START_FAILED = "start_failed"
    NOT_NEEDED = "not_needed"
    COOLING_DOWN = "cooling_down"
    OFF = "off"
    NOT_CHECKED = "not_checked"
