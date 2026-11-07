"""Define the CompactionScope enumeration."""

from __future__ import annotations

from enum import StrEnum


class CompactionScope(StrEnum):
    """Enumerate the granularity at which data files are compacted."""

    PARTITION = "partition"
    TABLE = "table"
