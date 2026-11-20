"""Define the Schema value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.shared.schema_field import SchemaField
from context.catalog.application.domain.model.shared.schema_field_at_path import SchemaFieldAtPath


class Schema(ValueObject):
    """One schema version of a table: its id and its top-level fields in order."""

    schema_id: int
    fields: tuple[SchemaField, ...]

    def field_named(self, name: str) -> SchemaField | None:
        """Return the top-level field called ``name``, or None."""
        return next((field for field in self.fields if field.name == name), None)

    def walk(self) -> tuple[SchemaFieldAtPath, ...]:
        """Return every field with its path, depth first: a field before its children, children in order."""
        return tuple(Schema._walk(self.fields, ()))

    @staticmethod
    def _walk(fields: tuple[SchemaField, ...], parent: tuple[str, ...]) -> list[SchemaFieldAtPath]:
        walked: list[SchemaFieldAtPath] = []
        for field in fields:
            path = (*parent, field.name)
            walked.append(SchemaFieldAtPath(path=path, field=field))
            walked.extend(Schema._walk(field.children, path))
        return walked
