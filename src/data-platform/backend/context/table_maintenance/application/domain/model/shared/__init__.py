"""Domain vocabulary shared across aggregates."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared.compute_size import (
    ComputeSize,
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
from context.table_maintenance.application.domain.model.shared.manifest_stats import (
    ManifestStats,
)
from context.table_maintenance.application.domain.model.shared.max_age import (
    MAX_AGE,
)
from context.table_maintenance.application.domain.model.shared.max_snapshots_to_keep import (
    MAX_SNAPSHOTS_TO_KEEP,
)
from context.table_maintenance.application.domain.model.shared.measurement import (
    Measurement,
)
from context.table_maintenance.application.domain.model.shared.measurement_comparison import (
    MeasurementComparison,
)
from context.table_maintenance.application.domain.model.shared.measurement_unit import (
    MeasurementUnit,
)
from context.table_maintenance.application.domain.model.shared.non_negative_duration import (
    NonNegativeDuration,
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
from context.table_maintenance.application.domain.model.shared.platform_compute_size import (
    PlatformComputeSize,
)
from context.table_maintenance.application.domain.model.shared.platform_settings import (
    PlatformSettings,
)
from context.table_maintenance.application.domain.model.shared.positive_duration import (
    PositiveDuration,
)
from context.table_maintenance.application.domain.model.shared.size_memory import (
    SizeMemory,
)
from context.table_maintenance.application.domain.model.shared.size_source import (
    SizeSource,
)
from context.table_maintenance.application.domain.model.shared.snapshot_info import (
    SnapshotInfo,
)
from context.table_maintenance.application.domain.model.shared.snapshot_retention import (
    SnapshotRetention,
)
from context.table_maintenance.application.domain.model.shared.spec_filter import (
    SpecFilter,
)
from context.table_maintenance.application.domain.model.shared.table_observation import (
    TableObservation,
)
from context.table_maintenance.application.domain.model.shared.table_priority import (
    TablePriority,
)
from context.table_maintenance.application.domain.model.shared.whole_seconds import (
    WholeSeconds,
)

__all__ = [
    "MAX_AGE",
    "MAX_SNAPSHOTS_TO_KEEP",
    "ComputeSize",
    "MaintenanceAssessment",
    "MaintenanceOperation",
    "MaintenancePlan",
    "ManifestStats",
    "Measurement",
    "MeasurementComparison",
    "MeasurementUnit",
    "NonNegativeDuration",
    "OperationAssessment",
    "OperationVerdict",
    "PartitionFieldInfo",
    "PartitionSpecInfo",
    "PartitionStats",
    "PlannedOperation",
    "PlatformSettings",
    "PlatformComputeSize",
    "PositiveDuration",
    "SizeMemory",
    "SizeSource",
    "SnapshotInfo",
    "SnapshotRetention",
    "SpecFilter",
    "TableObservation",
    "TablePriority",
    "WholeSeconds",
]
