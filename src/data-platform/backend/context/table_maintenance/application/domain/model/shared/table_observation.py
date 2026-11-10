"""Define the TableObservation value object."""

from __future__ import annotations

from base.model import ValueObject
from context.table_maintenance.application.domain.model.shared.manifest_stats import (
    ManifestStats,
)
from context.table_maintenance.application.domain.model.shared.partition_spec_info import (
    PartitionSpecInfo,
)
from context.table_maintenance.application.domain.model.shared.partition_stats import (
    PartitionStats,
)
from context.table_maintenance.application.domain.model.shared.snapshot_info import (
    SnapshotInfo,
)


class TableObservation(ValueObject):
    """Hold a point-in-time view of an Iceberg table's physical layout."""

    table_uuid: str
    properties: dict[str, str]
    current_snapshot_id: int | None
    specs: tuple[PartitionSpecInfo, ...]
    partitions: tuple[PartitionStats, ...]
    manifests: tuple[ManifestStats, ...]
    snapshots: tuple[SnapshotInfo, ...]
