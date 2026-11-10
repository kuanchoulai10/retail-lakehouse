"""Define the Schema value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.shared.schema_field import SchemaField


class Schema(ValueObject):
    """The current schema of a table: its id and its top-level fields in order."""

    schema_id: int
    fields: tuple[SchemaField, ...]

    def field_named(self, name: str) -> SchemaField | None:
        """Return the top-level field called ``name``, or None."""
        return next((field for field in self.fields if field.name == name), None)
