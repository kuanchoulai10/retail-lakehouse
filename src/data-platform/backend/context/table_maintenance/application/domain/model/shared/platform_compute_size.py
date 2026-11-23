"""Define the PlatformComputeSize value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.compute_size import ComputeSize


class PlatformComputeSize(ValueObject):
    """The resources of one compute size: coordinator and worker memory as the engine writes it, and the workers."""

    size: ComputeSize
    coordinator_memory: str
    worker_memory: str
    worker_count: int
