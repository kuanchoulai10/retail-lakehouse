"""Define the AttemptStatus enumeration."""

from __future__ import annotations

from enum import StrEnum


class AttemptStatus(StrEnum):
    """Enumerate the status of one attempt of a maintenance run.

    An attempt is submitted queued, runs once its coordinator starts, and ends succeeded or failed.
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
