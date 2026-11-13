"""Define the CompactionRoundActivity names."""

from __future__ import annotations

from enum import StrEnum


class CompactionRoundActivity(StrEnum):
    """Name the activities a compaction round workflow calls (besides the shared signal activity)."""

    SCHEDULE_COMPACTION_ROUND = "schedule_compaction_round"
