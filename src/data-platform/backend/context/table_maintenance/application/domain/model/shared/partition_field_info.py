"""Define the PartitionFieldInfo value object."""

from __future__ import annotations

from base.model import ValueObject


class PartitionFieldInfo(ValueObject):
    """Describe one field of an Iceberg partition spec in Iceberg's string forms."""

    field_id: int
    name: str
    source_column: str
    source_type: str
    transform: str
