"""Define the TableObservation value object."""

from __future__ import annotations

from typing import TYPE_CHECKING

from base import ReadOnlyMapping, ValueObject
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

if TYPE_CHECKING:
    from datetime import datetime


class TableObservation(ValueObject):
    """Hold a point-in-time view of an Iceberg table's physical layout."""

    table_uuid: str
    properties: ReadOnlyMapping[str, str]
    current_snapshot_id: int | None
    specs: tuple[PartitionSpecInfo, ...]
    partitions: tuple[PartitionStats, ...]
    manifests: tuple[ManifestStats, ...]
    snapshots: tuple[SnapshotInfo, ...]

    @property
    def last_committed_at(self) -> datetime | None:
        """Return the newest snapshot's commit time, or None for a table never committed to."""
        return max((s.committed_at for s in self.snapshots), default=None)
