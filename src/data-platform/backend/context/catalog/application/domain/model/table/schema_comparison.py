"""Define the SchemaComparison value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.table.schema_change import SchemaChange
from context.catalog.application.domain.model.table.schema_field_comparison import SchemaFieldComparison


class SchemaComparison(ValueObject):
    """Every field of a schema version set against a base version, matched by Iceberg field id.

    ``base_schema_id`` is None when there is no earlier version: every field is then listed
    unchanged.
    """

    base_schema_id: int | None
    schema_id: int
    fields: tuple[SchemaFieldComparison, ...]

    def change_counts(self) -> dict[SchemaChange, int]:
        """Return, for every kind of change (zeros included), the number of fields carrying it."""
        return {kind: sum(kind in field.changes for field in self.fields) for kind in SchemaChange}
