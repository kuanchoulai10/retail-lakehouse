"""Define the SchemaField value object."""

from __future__ import annotations

from base import ValueObject


class SchemaField(ValueObject):
    """One top-level column of a table schema.

    ``type`` is the Iceberg type as text. A primitive is its Iceberg name (``long``,
    ``decimal(10,2)``, ``fixed[16]``). A nested type is ``struct<name: type, ...>``,
    ``list<type>`` or ``map<key, value>``, where a nested field or element that is required
    carries ``required`` before its type (``struct<city: required string>``).

    ``children`` are the nested fields: a struct's fields in order, a list's one ``element``, a
    map's ``key`` and ``value``. Each carries its own Iceberg field id, so a nested field can be
    followed across schema versions.
    """

    id: int
    name: str
    type: str
    required: bool
    doc: str | None
    children: tuple[SchemaField, ...] = ()

    @property
    def outer_type(self) -> str:
        """Return ``struct``, ``list`` or ``map`` for a nested type, else the type text itself."""
        for kind in ("struct", "list", "map"):
            if self.type.startswith(f"{kind}<"):
                return kind
        return self.type
