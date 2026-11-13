"""Define the CandidateState enumeration."""

from __future__ import annotations

from enum import StrEnum


class CandidateState(StrEnum):
    """Enumerate where a compaction candidate stands.

    ``pending`` waits for a compaction round, ``held`` qualifies but is filtered
    out for now (or its table's compaction is not due), ``granted`` is picked by
    a round for its table's next run, ``claimed`` is taken by a run that has not
    submitted yet, ``running`` is being compacted, and ``done`` / ``failed`` say
    how its run ended until the next observation decides whether the partition
    is healthy.
    """

    PENDING = "pending"
    HELD = "held"
    GRANTED = "granted"
    CLAIMED = "claimed"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"

    @property
    def holds_a_claim(self) -> bool:
        """Return whether a run holds the candidate under a lease."""
        return self in {CandidateState.CLAIMED, CandidateState.RUNNING}

    @property
    def holds_a_lease(self) -> bool:
        """Return whether a round's grant or a run's claim holds the candidate until a lease ends."""
        return self is CandidateState.GRANTED or self.holds_a_claim

    @property
    def awaits_a_run(self) -> bool:
        """Return whether the candidate waits for a run to take it: pending, or granted and not yet claimed."""
        return self in {CandidateState.PENDING, CandidateState.GRANTED}

    @property
    def finished(self) -> bool:
        """Return whether the candidate's run has ended."""
        return self in {CandidateState.DONE, CandidateState.FAILED}
