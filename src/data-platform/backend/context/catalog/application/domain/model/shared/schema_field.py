"""Define the SchemaField value object."""

from __future__ import annotations

from base.model import ValueObject


class SchemaField(ValueObject):
    """One top-level column of a table schema.

    ``type`` is the Iceberg type as text. A primitive is its Iceberg name (``long``,
    ``decimal(10,2)``, ``fixed[16]``). A nested type is ``struct<name: type, ...>``,
    ``list<type>`` or ``map<key, value>``, where a nested field or element that is required
    carries ``required`` before its type (``struct<city: required string>``).
    """

    id: int
    name: str
    type: str
    required: bool
    doc: str | None
