"""Define the PartitionSpec value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from context.catalog.application.domain.model.table.partition_field import PartitionField


@dataclass(frozen=True)
class PartitionSpec(ValueObject):
    """The default partition spec of a table; no fields means the table is unpartitioned."""

    spec_id: int
    fields: tuple[PartitionField, ...]

    @classmethod
    def unpartitioned(cls) -> PartitionSpec:
        """Return the spec of an unpartitioned table."""
        return cls(spec_id=0, fields=())
