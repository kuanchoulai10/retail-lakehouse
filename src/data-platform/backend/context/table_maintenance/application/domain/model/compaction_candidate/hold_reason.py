"""Define the HoldReason enumeration."""

from __future__ import annotations

from enum import StrEnum


class HoldReason(StrEnum):
    """Enumerate why a qualifying partition is held back from compaction.

    ``too_small`` and ``recently_written`` are the candidate filters;
    ``not_due`` means the table's compaction is not due now (cooldown, trigger
    not met, needs attention, the operation off or a dry run), so a compaction
    round does not spend budget on it.
    """

    TOO_SMALL = "too_small"
    RECENTLY_WRITTEN = "recently_written"
    NOT_DUE = "not_due"
