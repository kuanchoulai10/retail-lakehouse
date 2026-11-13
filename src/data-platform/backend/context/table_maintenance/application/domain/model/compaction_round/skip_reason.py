"""Define the SkipReason enumeration."""

from __future__ import annotations

from enum import StrEnum


class SkipReason(StrEnum):
    """Enumerate why a compaction round left a pending candidate for a later round.

    ``budget_used`` means the round's GB·hour budget ran out before it (once one
    candidate does not fit, every one after it is skipped, so the order holds);
    ``table_share_used`` means its table already got as many partitions as one
    run compacts; ``table_busy`` means its table holds a live grant or run (or
    a run that finished since the table was last observed), so its next run is
    already decided.
    """

    BUDGET_USED = "budget_used"
    TABLE_SHARE_USED = "table_share_used"
    TABLE_BUSY = "table_busy"
