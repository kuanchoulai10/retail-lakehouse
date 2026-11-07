"""Map PyIceberg file listings to the primitive TableStorageMeasure."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.port.outbound.table import (
    TableStorageMeasure,
)

if TYPE_CHECKING:
    from pyiceberg.table import Table


def storage_measure_from_table(table: Table) -> TableStorageMeasure:
    """Measure the current snapshot's files and every snapshot's distinct files."""
    table_uuid = str(table.metadata.table_uuid)
    if table.current_snapshot() is None:
        return TableStorageMeasure(table_uuid, 0, 0, 0, 0)
    current = _sizes(table.inspect.files().to_pylist())
    referenced = _sizes(table.inspect.all_files().to_pylist())
    return TableStorageMeasure(
        table_uuid=table_uuid,
        current_bytes=sum(current.values()),
        current_files=len(current),
        referenced_bytes=sum(referenced.values()),
        referenced_files=len(referenced),
    )


def _sizes(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {str(row["file_path"]): int(row["file_size_in_bytes"]) for row in rows}
