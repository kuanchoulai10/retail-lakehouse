"""Define the PartitionField value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.table.partition_transform import PartitionTransform


class PartitionField(ValueObject):
    """One field of a partition spec: the source column id, the field's own id, its name and its transform."""

    source_id: int
    field_id: int
    name: str
    transform: PartitionTransform
