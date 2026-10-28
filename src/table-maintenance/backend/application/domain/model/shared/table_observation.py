"""Define the TableObservation value object."""

from __future__ import annotations

from dataclasses import dataclass

from application.domain.model.shared.manifest_stats import ManifestStats
from application.domain.model.shared.partition_spec_info import PartitionSpecInfo
from application.domain.model.shared.partition_stats import PartitionStats
from application.domain.model.shared.snapshot_info import SnapshotInfo
from base.value_object import ValueObject


@dataclass(frozen=True)
class TableObservation(ValueObject):
    """Hold a point-in-time view of an Iceberg table's physical layout."""

    table_uuid: str
    properties: dict[str, str]
    current_snapshot_id: int | None
    specs: tuple[PartitionSpecInfo, ...]
    partitions: tuple[PartitionStats, ...]
    manifests: tuple[ManifestStats, ...]
    snapshots: tuple[SnapshotInfo, ...]
