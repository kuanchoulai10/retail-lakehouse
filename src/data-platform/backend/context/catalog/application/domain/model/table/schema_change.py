"""Define the SchemaChange enum."""

from __future__ import annotations

from enum import StrEnum


class SchemaChange(StrEnum):
    """One kind of change a schema version makes to a field, matched by field id."""

    ADDED = "added"
    REMOVED = "removed"
    RENAMED = "renamed"
    TYPE_CHANGED = "type_changed"
    NULLABILITY_CHANGED = "nullability_changed"
    DOC_CHANGED = "doc_changed"
