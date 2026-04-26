"""Define the TriggerType enumeration."""

from enum import StrEnum


class TriggerType(StrEnum):
    """Enumerate how a job run was triggered."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
