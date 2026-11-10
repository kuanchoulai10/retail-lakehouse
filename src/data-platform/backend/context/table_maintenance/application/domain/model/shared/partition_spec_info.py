"""Define the PartitionSpecInfo value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.partition_field_info import (
    PartitionFieldInfo,
)


class PartitionSpecInfo(ValueObject):
    """Describe one partition spec of a table."""

    spec_id: int
    fields: tuple[PartitionFieldInfo, ...]

    @property
    def is_unpartitioned(self) -> bool:
        """Return whether the spec has no fields or only void transforms."""
        return all(f.transform == "void" for f in self.fields)
