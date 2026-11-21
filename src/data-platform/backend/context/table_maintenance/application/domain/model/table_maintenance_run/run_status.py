"""Define the RunStatus enumeration."""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    """Enumerate the status of a maintenance run and of each of its attempts.

    A run is pending until its first attempt is submitted and skipped when it never starts. An attempt is
    only ever queued, running, succeeded or failed.
    """

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
