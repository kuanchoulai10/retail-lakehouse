"""Define the PartitionChange enum."""

from __future__ import annotations

from enum import StrEnum


class PartitionChange(StrEnum):
    """One kind of change a partition spec makes to a partition field."""

    ADDED = "added"
    REMOVED = "removed"
    RENAMED = "renamed"
    TRANSFORM_CHANGED = "transform_changed"
