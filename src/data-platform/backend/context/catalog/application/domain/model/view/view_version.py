"""Define the ViewVersion value object."""

from __future__ import annotations

from base import ValueObject


class ViewVersion(ValueObject):
    """One version of a view: when it was made, its schema, its query (the SQL text), its dialect and namespace."""

    version_id: int
    timestamp_ms: int
    schema_id: int
    query: str
    dialect: str
    default_namespace: tuple[str, ...]
