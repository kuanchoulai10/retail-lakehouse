"""Define the PlannedOperation value object."""

from __future__ import annotations

from dataclasses import dataclass

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.shared.partition_stats import (
    PartitionStats,
)


@dataclass(frozen=True)
class PlannedOperation(ValueObject):
    """Name one operation to run; empty ``partitions`` means the whole table."""

    operation: MaintenanceOperation
    partitions: tuple[PartitionStats, ...] = ()
