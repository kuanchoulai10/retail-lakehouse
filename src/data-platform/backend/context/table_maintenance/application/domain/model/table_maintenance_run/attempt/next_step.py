"""Define the NextStep enumeration."""

from __future__ import annotations

from enum import StrEnum


class NextStep(StrEnum):
    """Enumerate what the platform does after a maintenance attempt ends."""

    DONE = "done"
    RETRY_LARGER = "retry_larger"
    RETRY_SAME = "retry_same"
    NEEDS_ATTENTION = "needs_attention"
    ATTEMPTS_USED = "attempts_used"
    NOT_RETRIED = "not_retried"
    CANCELLED = "cancelled"
    STILL_RUNNING = "still_running"

    @property
    def retries(self) -> bool:
        """Return whether this step submits another attempt."""
        return self in {NextStep.RETRY_LARGER, NextStep.RETRY_SAME}
