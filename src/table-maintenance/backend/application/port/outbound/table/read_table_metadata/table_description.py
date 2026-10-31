"""Define the TableDescription."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TableDescription:
    """A primitive description of a table's current definition.

    ``schema_fields`` items are ``{"field_id", "name", "type", "required"}`` of
    the current schema. ``specs`` have the shape of
    ``TableMetadataObservation.specs``. ``last_committed_at`` is the ISO-8601
    time of the current snapshot.
    """

    table_uuid: str
    format_version: int
    location: str
    properties: dict[str, str] = field(default_factory=dict)
    schema_fields: list[dict[str, Any]] = field(default_factory=list)
    specs: list[dict[str, Any]] = field(default_factory=list)
    current_snapshot_id: int | None = None
    current_summary: dict[str, str] = field(default_factory=dict)
    snapshot_count: int = 0
    last_committed_at: str | None = None
