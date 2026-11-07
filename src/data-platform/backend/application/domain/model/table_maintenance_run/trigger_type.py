"""Define the TriggerType enumeration."""

from __future__ import annotations

from enum import StrEnum


class TriggerType(StrEnum):
    """Enumerate what caused a maintenance run."""

    SCHEDULED = "scheduled"
    EVENT = "event"
    MANUAL = "manual"
