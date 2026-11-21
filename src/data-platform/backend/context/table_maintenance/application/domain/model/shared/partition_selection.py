"""Define the PartitionSelection value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.partition_stats import PartitionStats


class PartitionSelection(ValueObject):
    """Hold which over-target partitions a compaction job takes and which wait for writes to settle.

    ``selected`` is in the order the job takes them: partitions over the target for the longest wait
    first, oldest ``since`` first, then the rest, most reducible files first. ``waiting`` is most
    reducible files first. ``waiting_until`` is the earliest time a waiting
    partition is allowed to run, or None when none waits.
    """

    selected: tuple[PartitionStats, ...] = ()
    waiting: tuple[PartitionStats, ...] = ()
    waiting_until: datetime | None = None

    @property
    def all_waiting(self) -> bool:
        """Return whether partitions wait and none is selected."""
        return bool(self.waiting) and not self.selected
