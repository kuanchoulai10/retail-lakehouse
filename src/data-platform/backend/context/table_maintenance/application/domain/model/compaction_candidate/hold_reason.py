"""Define the HoldReason enumeration."""

from __future__ import annotations

from enum import StrEnum


class HoldReason(StrEnum):
    """Enumerate why a qualifying partition is held back from compaction."""

    TOO_SMALL = "too_small"
    RECENTLY_WRITTEN = "recently_written"
