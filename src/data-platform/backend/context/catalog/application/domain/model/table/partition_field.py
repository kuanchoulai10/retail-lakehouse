"""Define the PartitionField value object."""

from __future__ import annotations

from base import ValueObject


class PartitionField(ValueObject):
    """One field of a partition spec: the source column id, the field's own id, its name and its transform.

    ``transform`` is the Iceberg transform as text: ``identity``, ``year``, ``month``, ``day``,
    ``hour``, ``void``, ``bucket[N]`` or ``truncate[W]``.
    """

    source_id: int
    field_id: int
    name: str
    transform: str
