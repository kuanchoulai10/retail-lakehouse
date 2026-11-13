"""Define the CandidateState enumeration."""

from __future__ import annotations

from enum import StrEnum


class CandidateState(StrEnum):
    """Enumerate where a compaction candidate stands.

    ``pending`` waits to be picked, ``held`` qualifies but is filtered out for now,
    ``claimed`` is picked by a run that has not submitted yet, ``running`` is being
    compacted, and ``done`` / ``failed`` say how its run ended until the next
    observation decides whether the partition is healthy.
    """

    PENDING = "pending"
    HELD = "held"
    CLAIMED = "claimed"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

    @property
    def holds_a_claim(self) -> bool:
        """Return whether a run holds the candidate under a lease."""
        return self in {CandidateState.CLAIMED, CandidateState.RUNNING}

    @property
    def finished(self) -> bool:
        """Return whether the candidate's run has ended."""
        return self in {CandidateState.DONE, CandidateState.FAILED}
