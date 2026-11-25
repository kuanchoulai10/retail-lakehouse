"""Define the RunStatusName enumeration."""

from __future__ import annotations

from enum import StrEnum


class RunStatusName(StrEnum):
    """Enumerate the names of a maintenance run's statuses, as stored and shown.

    A run is pending until its first attempt is submitted, queued and then running while an attempt is in
    flight, and waiting to retry between a failed attempt and the next one. It ends succeeded, failed,
    skipped when it never starts, or cancelled.
    """

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAITING = "retry_waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
