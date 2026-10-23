"""Define the ReadCatalogGatewayObservation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ReadCatalogGatewayObservation:
    """A primitive snapshot of a table's statistics.

    ``specs`` items are ``{"spec_id", "fields": [{"field_id", "name",
    "source_column", "source_type", "transform"}]}``. ``partitions`` items are
    ``{"spec_id", "values", "data_file_count", "position_delete_file_count",
    "equality_delete_file_count", "total_data_file_size_bytes"}``. ``manifests``
    items are ``{"length_bytes"}``. ``snapshots`` items are ``{"snapshot_id",
    "committed_at"}`` with an ISO-8601 timestamp.
    """

    table_uuid: str
    properties: dict[str, str] = field(default_factory=dict)
    current_snapshot_id: int | None = None
    specs: list[dict[str, Any]] = field(default_factory=list)
    partitions: list[dict[str, Any]] = field(default_factory=list)
    manifests: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[dict[str, Any]] = field(default_factory=list)
