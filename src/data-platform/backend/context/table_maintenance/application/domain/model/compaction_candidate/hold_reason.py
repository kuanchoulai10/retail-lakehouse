"""Define the HoldReason enumeration."""

from __future__ import annotations

from enum import StrEnum


class HoldReason(StrEnum):
    """Enumerate why a qualifying partition is held back from compaction.

    ``too_small`` and ``recently_written`` are the candidate filters. The other
    two mean the table's compaction cannot run now, so a compaction round does
    not spend budget on it: ``cooldown`` while compaction waits out its
    cooldown (the candidate's wait for a round goes on, since the cooldown is
    the table's own wait), ``not_due`` for every other cause (a dry run, the
    operation off, needs attention, trigger not met), which ends the wait.
    """

    TOO_SMALL = "too_small"
    RECENTLY_WRITTEN = "recently_written"
    NOT_DUE = "not_due"
    COOLDOWN = "cooldown"
