"""Define the table_output_fields function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import Table


def table_output_fields(table: Table) -> dict[str, Any]:
    """Return the primitive fields shared by the Get, Create and UpdateProperties table outputs."""
    return {
        "catalog": table.id.catalog,
        "namespace": list(table.id.namespace),
        "name": table.id.name,
        "uuid": table.uuid,
        "format_version": table.format_version,
        "location": table.location,
        "current_snapshot_id": table.current_snapshot_id,
        "last_updated_ms": table.last_updated_ms,
        "schema": {
            "schema_id": table.current_schema.schema_id,
            "fields": [
                {"id": f.id, "name": f.name, "type": f.type, "required": f.required, "doc": f.doc}
                for f in table.current_schema.fields
            ],
        },
        "partition_spec": {
            "spec_id": table.partition_spec.spec_id,
            "fields": [
                {"source_id": f.source_id, "field_id": f.field_id, "name": f.name, "transform": f.transform}
                for f in table.partition_spec.fields
            ],
        },
        "sort_order": {
            "order_id": table.sort_order.order_id,
            "fields": [
                {
                    "source_id": f.source_id,
                    "transform": f.transform,
                    "direction": str(f.direction),
                    "null_order": str(f.null_order),
                }
                for f in table.sort_order.fields
            ],
        },
        "snapshots": [
            {
                "id": s.snapshot_id,
                "parent_id": s.parent_id,
                "timestamp_ms": s.timestamp_ms,
                "operation": s.operation,
                "summary": dict(s.summary),
            }
            for s in table.snapshots
        ],
        "properties": dict(table.properties),
        "summary": {
            "total_records": table.summary.total_records,
            "total_data_files": table.summary.total_data_files,
            "total_files_size": table.summary.total_files_size,
        },
    }
