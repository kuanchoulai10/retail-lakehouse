"""Define the OperationRunStatus enumeration."""

from __future__ import annotations

from enum import StrEnum


class OperationRunStatus(StrEnum):
    """Enumerate the status of one operation within a maintenance run."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
