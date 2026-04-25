"""Define the TableSchema value object."""

from __future__ import annotations

from dataclasses import dataclass

from core.base.value_object import ValueObject
from application.domain.model.catalog.schema_field import SchemaField


@dataclass(frozen=True)
class TableSchema(ValueObject):
    """Immutable schema composed of ordered fields."""

    fields: tuple[SchemaField, ...]
