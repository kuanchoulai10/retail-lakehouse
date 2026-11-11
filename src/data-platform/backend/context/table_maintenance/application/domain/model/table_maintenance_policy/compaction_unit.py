"""Define the CompactionUnit enumeration."""

from __future__ import annotations

from enum import StrEnum


class CompactionUnit(StrEnum):
    """Enumerate the units a compaction is run over."""

    PARTITION = "partition"
    TABLE = "table"
