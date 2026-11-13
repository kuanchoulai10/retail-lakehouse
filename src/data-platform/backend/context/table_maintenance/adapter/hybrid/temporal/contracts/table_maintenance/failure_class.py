"""Define the MaintenanceFailureClass workflow contract."""

from __future__ import annotations

from enum import StrEnum


class MaintenanceFailureClass(StrEnum):
    """Name why a recorded attempt failed, as the record activity replies it."""

    OOM = "oom"
    TIMEOUT = "timeout"
    COMMIT_CONFLICT = "commit_conflict"
    PERMANENT = "permanent"
    CANCELLED = "cancelled"
    OTHER = "other"
