"""Define the TableMetrics value object."""

from __future__ import annotations

from pydantic import AwareDatetime, NonNegativeInt

from base import ValueObject
from context.table_maintenance.application.domain.model.table.table_id import TableId

TABLE_METRIC_COUNT_FIELDS: tuple[str, ...] = (
    "data_files",
    "position_delete_files",
    "equality_delete_files",
    "deletion_vectors",
    "data_size_bytes",
    "data_records",
    "position_delete_records",
    "equality_delete_records",
    "reducible_files",
    "manifests",
    "manifests_size_bytes",
    "manifest_added_entries",
    "manifest_existing_entries",
    "manifest_deleted_entries",
    "snapshots",
)


class TableMetrics(ValueObject):
    """Hold what one reconcile measured of a table's files, manifests and snapshots.

    ``position_delete_files`` excludes deletion vectors, which ``deletion_vectors`` counts, so
    the four file counts sum to every live file; ``position_delete_records`` includes the
    deletion vectors' records. ``data_records`` is the sum over data files, not the rows left
    after deletes, which metadata cannot tell when equality deletes exist.
    """

    table_id: TableId
    observed_at: AwareDatetime
    data_files: NonNegativeInt
    position_delete_files: NonNegativeInt
    equality_delete_files: NonNegativeInt
    deletion_vectors: NonNegativeInt
    data_size_bytes: NonNegativeInt
    data_records: NonNegativeInt
    position_delete_records: NonNegativeInt
    equality_delete_records: NonNegativeInt
    reducible_files: NonNegativeInt
    manifests: NonNegativeInt
    manifests_size_bytes: NonNegativeInt
    manifest_added_entries: NonNegativeInt
    manifest_existing_entries: NonNegativeInt
    manifest_deleted_entries: NonNegativeInt
    snapshots: NonNegativeInt
