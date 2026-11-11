"""Domain vocabulary shared across aggregates."""

from __future__ import annotations

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
from context.table_maintenance.application.domain.model.shared.positive_duration import (
    PositiveDuration,
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
    "PositiveDuration",
    "SizeSource",
    "SnapshotInfo",
    "SpecFilter",
    "TableObservation",
]
