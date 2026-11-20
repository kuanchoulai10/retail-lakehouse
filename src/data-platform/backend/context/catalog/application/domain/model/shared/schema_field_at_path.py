"""Define the SchemaFieldAtPath value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.shared.schema_field import SchemaField


class SchemaFieldAtPath(ValueObject):
    """A schema field with its path from the top level: ``("shipping", "city")`` for a nested one."""

    path: tuple[str, ...]
    field: SchemaField

    @property
    def depth(self) -> int:
        """Return how deep the field sits: 0 for a top-level field."""
        return len(self.path) - 1
