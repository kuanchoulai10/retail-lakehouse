"""Define the SchemaFieldComparison value object."""

from __future__ import annotations

from base import ValueObject
from context.catalog.application.domain.model.table.schema_change import SchemaChange


class SchemaFieldComparison(ValueObject):
    """One field of a schema comparison: its current and previous state, matched by field id.

    The current side (``path``, ``type``, ``required``, ``doc``) is None for a removed field and
    the previous side (``previous_*``) is None for an added one. ``type`` is the outer type
    (``struct``, ``list``, ``map`` or the primitive), because a nested field's children are rows
    of their own. ``depth`` is the depth in the newer schema, or in the base for a removed field.
    ``changes`` lists what changed, in ``SchemaChange`` order; empty means unchanged.
    """

    field_id: int
    depth: int
    path: tuple[str, ...] | None
    previous_path: tuple[str, ...] | None
    type: str | None
    previous_type: str | None
    required: bool | None
    previous_required: bool | None
    doc: str | None
    previous_doc: str | None
    changes: tuple[SchemaChange, ...]
