"""Define the PartitionFieldComparison value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.table.partition_change import PartitionChange


def _expression(transform: str | None, source_path: tuple[str, ...] | None) -> str | None:
    if transform is None or source_path is None or transform == "void":
        return None
    return f"{transform}({'.'.join(source_path)})"


class PartitionFieldComparison(ValueObject):
    """One field of a partition spec comparison: its current and previous state.

    The current side (``field_id``, ``name``, ``source_path``, ``transform``) is None for a removed
    field and the previous side (``previous_*``) is None for an added one. A field whose transform
    changed carries its new partition field id in ``field_id`` and the old one in
    ``previous_field_id``. ``changes`` lists what changed, in ``PartitionChange`` order; empty
    means unchanged.
    """

    field_id: int | None
    previous_field_id: int | None
    name: str | None
    previous_name: str | None
    source_path: tuple[str, ...] | None
    previous_source_path: tuple[str, ...] | None
    transform: str | None
    previous_transform: str | None
    changes: tuple[PartitionChange, ...]

    def expression(self) -> str | None:
        """Return ``transform(source path)``, or None for a removed field or a ``void`` transform."""
        return _expression(self.transform, self.source_path)

    def previous_expression(self) -> str | None:
        """Return the previous ``transform(source path)``, or None for an added field or a ``void`` transform."""
        return _expression(self.previous_transform, self.previous_source_path)
