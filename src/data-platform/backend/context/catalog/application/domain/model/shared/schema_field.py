"""Define the SchemaField value object."""

from __future__ import annotations

from pydantic import model_validator

from base import ValueObject
from context.catalog.application.domain.model.shared.schema_field_kind import SchemaFieldKind


class SchemaField(ValueObject):
    """One field of a table schema: a top-level column, or a field nested in one through ``children``.

    ``type`` is the Iceberg type as text. A primitive is its Iceberg name (``long``,
    ``decimal(10,2)``, ``fixed[16]``). A nested type is ``struct<name: type, ...>``,
    ``list<type>`` or ``map<key, value>``, where a nested field or element that is required
    carries ``required`` before its type (``struct<city: required string>``).

    ``kind`` says whether the type is a primitive, a struct, a list or a map. It is set by
    whoever reads the type's structure, such as the catalog's metadata; a field known only by its
    type text, as the create table form gives it, is ``primitive``.

    ``children`` are the nested fields: a struct's fields in order, a list's one ``element``, a
    map's ``key`` and ``value``. Each is a ``SchemaField`` of its own, with its own Iceberg field
    id and its own children, so a nested field at any depth can be followed across schema
    versions. A primitive has none.
    """

    id: int
    name: str
    type: str
    required: bool
    doc: str | None
    kind: SchemaFieldKind = SchemaFieldKind.PRIMITIVE
    children: tuple[SchemaField, ...] = ()

    @model_validator(mode="after")
    def _only_a_nested_field_has_children(self) -> SchemaField:
        if self.kind is SchemaFieldKind.PRIMITIVE and self.children:
            raise ValueError(f"primitive field {self.name} cannot have nested fields")
        return self

    @property
    def outer_type(self) -> str:
        """Return ``struct``, ``list`` or ``map`` for a nested field, else the primitive's type text."""
        if self.kind is SchemaFieldKind.PRIMITIVE:
            return self.type
        return str(self.kind)
