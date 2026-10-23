"""Define the PlannedOperation value object."""

from __future__ import annotations

from dataclasses import dataclass

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.observation.partition_stats import PartitionStats
from base.value_object import ValueObject


@dataclass(frozen=True)
class PlannedOperation(ValueObject):
    """Name one operation to run; empty ``partitions`` means the whole table."""

    operation: MaintenanceOperation
    partitions: tuple[PartitionStats, ...] = ()
