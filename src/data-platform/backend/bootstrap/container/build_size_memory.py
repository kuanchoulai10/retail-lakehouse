"""Provide the build_size_memory function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import spark_memory_bytes
from context.table_maintenance.application.domain.model.shared import ComputeSize, SizeMemory

if TYPE_CHECKING:
    from bootstrap.configs import SparkSettings, SparkSizeSettings


def build_size_memory(settings: SparkSettings) -> dict[ComputeSize, SizeMemory]:
    """Return the driver and executor memory each compute size runs with, from the Spark settings."""
    sizes = {ComputeSize.S: settings.size_s, ComputeSize.M: settings.size_m, ComputeSize.L: settings.size_l}
    return {size: _memory(resources) for size, resources in sizes.items()}


def _memory(resources: SparkSizeSettings) -> SizeMemory:
    return SizeMemory(
        driver_bytes=spark_memory_bytes(resources.driver_memory),
        executor_bytes=spark_memory_bytes(resources.executor_memory),
    )
