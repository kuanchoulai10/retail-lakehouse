"""Define the FailureClass enumeration."""

from __future__ import annotations

from enum import StrEnum


class FailureClass(StrEnum):
    """Enumerate why a maintenance attempt failed, as far as its evidence tells."""

    OOM = "oom"
    TIMEOUT = "timeout"
    COMMIT_CONFLICT = "commit_conflict"
    PERMANENT = "permanent"
    CANCELLED = "cancelled"
    OTHER = "other"
