"""Define the PartitionFieldComparison value object."""

from __future__ import annotations

from pydantic import model_validator

from base import ValueObject
from context.catalog.application.domain.model.table.partition_change import PartitionChange
from context.catalog.application.domain.model.table.partition_transform import PartitionTransform
from context.catalog.application.domain.model.table.partition_transform_kind import PartitionTransformKind


class PartitionFieldComparison(ValueObject):
    """One field of a partition spec comparison: its current and previous state.

    The current side (``field_id``, ``name``, ``source_id``, ``source_path``, ``transform``) is
    None for a removed field and the previous side (``previous_*``) is None for an added one. A
    side that is there but whose source column no schema holds has its ``source_id`` and no
    ``source_path``. A field whose transform changed carries its new partition field id in
    ``field_id`` and the old one in ``previous_field_id``. Neither side is ever a ``void``
    transform, which is a dropped field. ``changes`` lists what changed, in ``PartitionChange``
    order; empty means unchanged.
    """

    field_id: int | None
    previous_field_id: int | None
    name: str | None
    previous_name: str | None
    source_id: int | None
    previous_source_id: int | None
    source_path: tuple[str, ...] | None
    previous_source_path: tuple[str, ...] | None
    transform: PartitionTransform | None
    previous_transform: PartitionTransform | None
    changes: tuple[PartitionChange, ...]

    @model_validator(mode="after")
    def _no_side_is_void(self) -> PartitionFieldComparison:
        for transform in (self.transform, self.previous_transform):
            if transform is not None and transform.kind is PartitionTransformKind.VOID:
                raise ValueError("a void partition field is a dropped one and has no comparison row")
        return self
