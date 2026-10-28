"""Define the RunStatus enumeration."""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    """Enumerate the derived status of a maintenance run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIALLY_FAILED = "partially_failed"
    FAILED = "failed"
