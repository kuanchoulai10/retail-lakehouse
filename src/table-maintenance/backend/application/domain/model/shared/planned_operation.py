"""Define the PlannedOperation value object."""

from __future__ import annotations

from dataclasses import dataclass

from application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.shared.partition_stats import PartitionStats
from base import ValueObject


@dataclass(frozen=True)
class PlannedOperation(ValueObject):
    """Name one operation to run; empty ``partitions`` means the whole table."""

    operation: MaintenanceOperation
    partitions: tuple[PartitionStats, ...] = ()
