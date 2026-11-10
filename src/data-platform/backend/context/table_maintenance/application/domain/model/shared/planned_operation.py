"""Define the PlannedOperation value object."""

from __future__ import annotations

from base.model import ValueObject
from context.table_maintenance.application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.shared.partition_stats import (
    PartitionStats,
)


class PlannedOperation(ValueObject):
    """Name one operation to run; empty ``partitions`` means the whole table."""

    operation: MaintenanceOperation
    partitions: tuple[PartitionStats, ...] = ()
