"""Define the AttemptEnding enumeration."""

from __future__ import annotations

from enum import StrEnum


class AttemptEnding(StrEnum):
    """Enumerate how the platform saw a maintenance attempt end."""

    RESULT = "result"
    JOB_FAILED = "job_failed"
    TIMED_OUT = "timed_out"
    MISSING = "missing"
    CANCELLED = "cancelled"
    SUBMIT_FAILED = "submit_failed"
    ADMISSION_FAILED = "admission_failed"
