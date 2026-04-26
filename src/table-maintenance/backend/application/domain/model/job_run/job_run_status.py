"""Define the JobRunStatus enumeration with state transition rules."""

from __future__ import annotations

from enum import StrEnum


class JobRunStatus(StrEnum):
    """Enumerate the lifecycle states of a job run execution.

    State machine::

        PENDING ──> RUNNING ──> COMPLETED
           │           │
           │           ├──> FAILED
           │           │
           │           └──> CANCELLED
           │
           ├──> FAILED
           │
           └──> CANCELLED
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def can_transition_to(self, target: JobRunStatus) -> bool:
        """Return True if transitioning from this state to target is allowed."""
        return target in _TRANSITIONS[self]


_TRANSITIONS: dict[JobRunStatus, frozenset[JobRunStatus]] = {
    JobRunStatus.PENDING: frozenset(
        {JobRunStatus.RUNNING, JobRunStatus.FAILED, JobRunStatus.CANCELLED}
    ),
    JobRunStatus.RUNNING: frozenset(
        {JobRunStatus.COMPLETED, JobRunStatus.FAILED, JobRunStatus.CANCELLED}
    ),
    JobRunStatus.COMPLETED: frozenset(),
    JobRunStatus.FAILED: frozenset(),
    JobRunStatus.CANCELLED: frozenset(),
}
