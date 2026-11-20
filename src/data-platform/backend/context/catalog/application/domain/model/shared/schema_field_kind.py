"""Define the SchemaFieldKind enum."""

from __future__ import annotations

from enum import StrEnum


class SchemaFieldKind(StrEnum):
    """What a schema field's type is: a primitive, or one of Iceberg's three nested types."""

    PRIMITIVE = "primitive"
    STRUCT = "struct"
    LIST = "list"
    MAP = "map"
