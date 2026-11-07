"""Domain vocabulary shared across aggregates."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared.compaction_scope import (
    CompactionScope,
)
from context.table_maintenance.application.domain.model.shared.expire_snapshots_settings import (
    ExpireSnapshotsSettings,
)
from context.table_maintenance.application.domain.model.shared.invalid_maintenance_settings import (
    InvalidMaintenanceSettings,
)
from context.table_maintenance.application.domain.model.shared.maintenance_assessment import (
    MaintenanceAssessment,
)
from context.table_maintenance.application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.shared.maintenance_plan import (
    MaintenancePlan,
)
from context.table_maintenance.application.domain.model.shared.maintenance_settings import (
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.shared.manifest_stats import (
    ManifestStats,
)
from context.table_maintenance.application.domain.model.shared.operation_assessment import (
    OperationAssessment,
)
from context.table_maintenance.application.domain.model.shared.operation_verdict import (
    OperationVerdict,
)
from context.table_maintenance.application.domain.model.shared.partition_field_info import (
    PartitionFieldInfo,
)
from context.table_maintenance.application.domain.model.shared.partition_spec_info import (
    PartitionSpecInfo,
)
from context.table_maintenance.application.domain.model.shared.partition_stats import (
    PartitionStats,
)
from context.table_maintenance.application.domain.model.shared.planned_operation import (
    PlannedOperation,
)
from context.table_maintenance.application.domain.model.shared.remove_orphan_files_settings import (
    RemoveOrphanFilesSettings,
)
from context.table_maintenance.application.domain.model.shared.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)
from context.table_maintenance.application.domain.model.shared.rewrite_manifests_settings import (
    RewriteManifestsSettings,
)
from context.table_maintenance.application.domain.model.shared.size_source import (
    SizeSource,
)
from context.table_maintenance.application.domain.model.shared.snapshot_info import (
    SnapshotInfo,
)
from context.table_maintenance.application.domain.model.shared.spec_filter import (
    SpecFilter,
)
from context.table_maintenance.application.domain.model.shared.table_observation import (
    TableObservation,
)

__all__ = [
    "CompactionScope",
    "ExpireSnapshotsSettings",
    "InvalidMaintenanceSettings",
    "MaintenanceAssessment",
    "MaintenanceOperation",
    "MaintenancePlan",
    "MaintenanceSettings",
    "ManifestStats",
    "OperationAssessment",
    "OperationVerdict",
    "PartitionFieldInfo",
    "PartitionSpecInfo",
    "PartitionStats",
    "PlannedOperation",
    "RemoveOrphanFilesSettings",
    "RewriteDataFilesSettings",
    "RewriteManifestsSettings",
    "SizeSource",
    "SnapshotInfo",
    "SpecFilter",
    "TableObservation",
]
