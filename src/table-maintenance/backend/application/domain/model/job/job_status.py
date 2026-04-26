"""Define the JobStatus enumeration with state transition rules."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    """Enumerate the lifecycle states of a Job definition.

    State machine::

        ACTIVE ──> PAUSED ──> ARCHIVED
           │                     ^
           └─────────────────────┘
    """

    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"

    def can_transition_to(self, target: JobStatus) -> bool:
        """Return True if transitioning from this state to target is allowed."""
        return target in _TRANSITIONS[self]


_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.ACTIVE: frozenset({JobStatus.PAUSED, JobStatus.ARCHIVED}),
    JobStatus.PAUSED: frozenset({JobStatus.ACTIVE, JobStatus.ARCHIVED}),
    JobStatus.ARCHIVED: frozenset(),
}
