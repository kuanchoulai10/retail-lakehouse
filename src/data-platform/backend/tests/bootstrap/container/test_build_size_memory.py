"""Test the memory of each compute size built from the Spark settings."""

from __future__ import annotations

from bootstrap.configs import SparkSettings, SparkSizeSettings
from bootstrap.container import build_size_memory
from context.table_maintenance.application.domain.model.shared import ComputeSize, SizeMemory

MIB = 1024 * 1024


def test_default_sizes_give_each_role_its_configured_memory():
    """The default S, M and L sizes map to the driver and executor memory they run with."""
    memory = build_size_memory(SparkSettings())
    assert memory == {
        ComputeSize.S: SizeMemory(coordinator_bytes=768 * MIB, worker_bytes=768 * MIB),
        ComputeSize.M: SizeMemory(coordinator_bytes=1024 * MIB, worker_bytes=1536 * MIB),
        ComputeSize.L: SizeMemory(coordinator_bytes=1536 * MIB, worker_bytes=2048 * MIB),
    }


def test_overridden_size_uses_its_own_memory():
    """A size set in the settings is mapped from the memory set there."""
    memory = build_size_memory(SparkSettings(size_s=SparkSizeSettings(driver_memory="512m", executor_memory="1g")))
    assert memory[ComputeSize.S] == SizeMemory(coordinator_bytes=512 * MIB, worker_bytes=1024 * MIB)
