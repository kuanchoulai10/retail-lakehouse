"""Define the MaintenanceAttemptEnding workflow contract."""

from __future__ import annotations

from enum import StrEnum


class MaintenanceAttemptEnding(StrEnum):
    """Name how the maintenance workflow saw an attempt end, as sent to the record activity."""

    RESULT = "result"
    JOB_FAILED = "job_failed"
    TIMED_OUT = "timed_out"
    MISSING = "missing"
    CANCELLED = "cancelled"
    SUBMIT_FAILED = "submit_failed"
    QUEUE_TIMED_OUT = "queue_timed_out"
