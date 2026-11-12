"""Define the MaintenanceNextStep workflow contract."""

from __future__ import annotations

from enum import StrEnum


class MaintenanceNextStep(StrEnum):
    """Name what follows a recorded attempt, as the record activity replies it."""

    DONE = "done"
    RETRY_LARGER = "retry_larger"
    RETRY_SAME = "retry_same"
    NEEDS_ATTENTION = "needs_attention"
    ATTEMPTS_USED = "attempts_used"
    NOT_RETRIED = "not_retried"
    CANCELLED = "cancelled"
    STILL_RUNNING = "still_running"
