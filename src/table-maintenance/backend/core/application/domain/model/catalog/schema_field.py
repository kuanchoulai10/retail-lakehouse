"""Define the SchemaField value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject


@dataclass(frozen=True)
class SchemaField(ValueObject):
    """A single field in a table schema."""

    field_id: int
    name: str
    field_type: str
    required: bool
