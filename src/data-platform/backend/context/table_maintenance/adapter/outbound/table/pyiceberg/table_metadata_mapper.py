"""Map a PyIceberg table to the primitive TableMetadata."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.port.outbound.table import TableMetadata

if TYPE_CHECKING:
    from pyiceberg.table import Table

    from context.table_maintenance.application.port.outbound.table import TableMetadataRef


def table_metadata_from_table(ref: TableMetadataRef, table: Table) -> TableMetadata:
    """Locate the table by ``ref`` with its uuid and its newest snapshot's commit time, if any."""
    newest_ms = max((s.timestamp_ms for s in table.metadata.snapshots), default=None)
    return TableMetadata(
        catalog=ref.catalog,
        namespace=ref.namespace,
        table=ref.table,
        table_uuid=str(table.metadata.table_uuid),
        last_committed_at=(None if newest_ms is None else datetime.fromtimestamp(newest_ms / 1000, tz=UTC).isoformat()),
    )
