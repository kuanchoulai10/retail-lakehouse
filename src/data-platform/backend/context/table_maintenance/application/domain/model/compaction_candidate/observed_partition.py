"""Define the ObservedPartition value object."""

from __future__ import annotations

from datetime import datetime

from pydantic import NonNegativeInt

from base import ValueObject
from context.table_maintenance.application.domain.model.compaction_candidate.partition_key import (
    PartitionKey,
)


class ObservedPartition(ValueObject):
    """Hold what one observation found about a partition that meets the policy's compaction conditions.

    ``partition`` is ``PartitionKey.whole_table()`` for a compaction of the whole
    table, whose counts are then the whole table's.
    """

    partition: PartitionKey
    label: str
    reducible_files: NonNegativeInt
    data_bytes: NonNegativeInt
    last_written_at: datetime | None = None
