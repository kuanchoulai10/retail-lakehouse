"""Define the PlatformComputeSize value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.compute_size import ComputeSize


class PlatformComputeSize(ValueObject):
    """The Spark resources one compute size runs with: driver and executor memory as Spark writes it, and executors."""

    size: ComputeSize
    driver_memory: str
    executor_memory: str
    executor_instances: int
