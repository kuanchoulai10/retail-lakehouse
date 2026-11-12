"""Define the SparkSizeResources."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SparkSizeResources:
    """Hold the driver and executor memory and the executor count of one Spark size."""

    driver_memory: str
    executor_memory: str
    executor_instances: int = 1
