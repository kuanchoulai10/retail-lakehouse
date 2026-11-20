"""Define the PartitionSpec value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.table.partition_field import PartitionField


class PartitionSpec(ValueObject):
    """One partition spec of a table, by its id; no fields means it partitions nothing."""

    spec_id: int
    fields: tuple[PartitionField, ...]

    @classmethod
    def unpartitioned(cls) -> PartitionSpec:
        """Return the spec of an unpartitioned table."""
        return cls(spec_id=0, fields=())
