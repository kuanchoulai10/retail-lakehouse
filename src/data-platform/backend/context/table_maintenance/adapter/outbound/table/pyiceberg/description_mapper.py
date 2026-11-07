"""Map a PyIceberg table to the primitive TableDescription."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table.pyiceberg.observation_mapper import (
    spec_of,
)
from context.table_maintenance.application.port.outbound.table import TableDescription

if TYPE_CHECKING:
    from pyiceberg.table import Table


def description_from_table(table: Table) -> TableDescription:
    """Build the description of a table's current definition."""
    metadata = table.metadata
    snapshot = table.current_snapshot()
    return TableDescription(
        table_uuid=str(metadata.table_uuid),
        format_version=metadata.format_version,
        location=metadata.location,
        properties=dict(metadata.properties),
        schema_fields=[
            {
                "field_id": f.field_id,
                "name": f.name,
                "type": str(f.field_type),
                "required": f.required,
            }
            for f in table.schema().fields
        ],
        specs=[spec_of(table, spec) for spec in metadata.partition_specs],
        current_snapshot_id=snapshot.snapshot_id if snapshot else None,
        current_summary=_summary_of(snapshot),
        snapshot_count=len(metadata.snapshots),
        last_committed_at=(
            datetime.fromtimestamp(snapshot.timestamp_ms / 1000, tz=UTC).isoformat()
            if snapshot
            else None
        ),
    )


def _summary_of(snapshot: object) -> dict[str, str]:
    summary = getattr(snapshot, "summary", None)
    if summary is None:
        return {}
    return {"operation": str(summary.operation.value), **summary.additional_properties}
