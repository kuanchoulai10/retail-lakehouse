"""Define the JobRunStatus enumeration."""

from enum import StrEnum


class JobRunStatus(StrEnum):
    """Enumerate the lifecycle states of a job run execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"
