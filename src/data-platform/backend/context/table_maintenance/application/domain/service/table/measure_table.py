"""Define the measure_table domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableMetrics
from context.table_maintenance.application.domain.service.shared import resolve_target_file_size
from context.table_maintenance.application.domain.service.table.compute_reducible_files import (
    compute_reducible_files,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.shared import TableId, TableObservation


def measure_table(table_id: TableId, observation: TableObservation, observed_at: datetime) -> TableMetrics:
    """Return the table's metrics as of ``observed_at``, whatever its policy says.

    Reducible files are counted at the table's own target file size over every partition.
    """
    target = resolve_target_file_size(observation.properties)
    partitions = observation.partitions
    manifests = observation.manifests
    deletion_vectors = sum(p.deletion_vector_count for p in partitions)
    return TableMetrics(
        table_id=table_id,
        observed_at=observed_at,
        data_files=sum(p.data_file_count for p in partitions),
        position_delete_files=sum(p.position_delete_file_count for p in partitions) - deletion_vectors,
        equality_delete_files=sum(p.equality_delete_file_count for p in partitions),
        deletion_vectors=deletion_vectors,
        data_size_bytes=sum(p.total_data_file_size_bytes for p in partitions),
        data_records=sum(p.data_record_count for p in partitions),
        position_delete_records=sum(p.position_delete_record_count for p in partitions),
        equality_delete_records=sum(p.equality_delete_record_count for p in partitions),
        reducible_files=sum(compute_reducible_files(p, target) for p in partitions),
        manifests=len(manifests),
        manifests_size_bytes=sum(m.length_bytes for m in manifests),
        manifest_added_entries=sum(m.added_entries for m in manifests),
        manifest_existing_entries=sum(m.existing_entries for m in manifests),
        manifest_deleted_entries=sum(m.deleted_entries for m in manifests),
        snapshots=len(observation.snapshots),
    )
