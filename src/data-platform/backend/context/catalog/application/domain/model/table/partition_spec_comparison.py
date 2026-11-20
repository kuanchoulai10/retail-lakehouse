"""Define the PartitionSpecComparison value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.table.partition_change import PartitionChange
from context.catalog.application.domain.model.table.partition_field_comparison import PartitionFieldComparison


class PartitionSpecComparison(ValueObject):
    """Every field of a partition spec set against a base spec.

    ``base_spec_id`` is None when there is no earlier spec: every field is then listed unchanged.
    """

    base_spec_id: int | None
    spec_id: int
    fields: tuple[PartitionFieldComparison, ...]

    def change_counts(self) -> dict[PartitionChange, int]:
        """Return, for every kind of change (zeros included), the number of fields carrying it."""
        return {kind: sum(kind in field.changes for field in self.fields) for kind in PartitionChange}

    def field_count(self) -> int:
        """Return how many fields the newer spec has, not counting ``void`` ones."""
        return sum(field.field_id is not None for field in self.fields)
