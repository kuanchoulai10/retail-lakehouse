"""Define the Schema value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base import ValueObject

if TYPE_CHECKING:
    from context.catalog.application.domain.model.shared.schema_field import SchemaField


@dataclass(frozen=True)
class Schema(ValueObject):
    """The current schema of a table: its id and its top-level fields in order."""

    schema_id: int
    fields: tuple[SchemaField, ...]

    def field_named(self, name: str) -> SchemaField | None:
        """Return the top-level field called ``name``, or None."""
        return next((field for field in self.fields if field.name == name), None)
