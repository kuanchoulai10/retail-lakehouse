"""Define the OverTargetPartition value object."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared.partition_stats import PartitionStats


class OverTargetPartition(ValueObject):
    """Hold a partition that is over its compaction target, and since when.

    ``since`` is the time the first plan saw the partition over the target. A partition is
    identified by its ``spec_id`` and ``values``, so the same values in two specs are two
    partitions.
    """

    spec_id: int
    values: tuple[str | int | float | bool | None, ...]
    since: datetime

    def is_of(self, partition: PartitionStats) -> bool:
        """Return whether ``partition`` is the partition this value tracks."""
        return self.spec_id == partition.spec_id and self.values == partition.values
