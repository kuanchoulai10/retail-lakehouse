"""Define the table_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.table.polaris.partition_spec_from_polaris import (
    partition_spec_from_polaris,
)
from context.catalog.adapter.outbound.table.polaris.snapshot_from_polaris import snapshot_from_polaris
from context.catalog.adapter.outbound.table.polaris.sort_order_from_polaris import sort_order_from_polaris
from context.catalog.adapter.outbound.table.polaris.table_schema_from_polaris import (
    table_schema_from_polaris,
)
from context.catalog.application.port.outbound.table import Table

if TYPE_CHECKING:
    from collections.abc import Mapping

    from context.catalog.application.port.outbound.table import TableId

_NO_SNAPSHOT = -1


def table_from_polaris(table_id: TableId, metadata: Mapping[str, Any]) -> Table:
    """Map the ``metadata`` of a LoadTableResult or CommitTableResponse to a Table; v1's -1 snapshot id is none."""
    current = metadata.get("current-snapshot-id")
    return Table(
        id=table_id,
        uuid=str(metadata["table-uuid"]),
        format_version=int(metadata["format-version"]),
        location=str(metadata["location"]),
        current_snapshot_id=None if current in (None, _NO_SNAPSHOT) else int(current),
        last_updated_ms=int(metadata["last-updated-ms"]),
        schema=table_schema_from_polaris(metadata),
        partition_spec=partition_spec_from_polaris(metadata),
        sort_order=sort_order_from_polaris(metadata),
        snapshots=[snapshot_from_polaris(snapshot) for snapshot in metadata.get("snapshots") or []],
        properties={str(key): str(value) for key, value in (metadata.get("properties") or {}).items()},
    )
