"""Define the pod_group_resources function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_memory_bytes import spark_memory_bytes

if TYPE_CHECKING:
    from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s.spark_size_resources import (
        SparkSizeResources,
    )

_MIB = 1024**2
_MIN_OVERHEAD_BYTES = 384 * _MIB
_OVERHEAD_NUMERATOR = 2
_OVERHEAD_DENOMINATOR = 5


def pod_group_resources(resources: SparkSizeResources, driver_cores: int, executor_cores: int) -> dict[str, str]:
    """Return the cpu and memory a job's PodGroup holds in its queue.

    Each of the driver and every executor needs its memory plus PySpark's overhead,
    ``max(384Mi, 0.4 x memory)``; the memory is the sum of these, in whole MiB, and the
    cpu is the driver's cores plus the cores of every executor. The overhead is exact
    integer arithmetic in fifths of a byte, so the 0.4 factor does not round.
    """
    driver = spark_memory_bytes(resources.driver_memory)
    executor = spark_memory_bytes(resources.executor_memory)
    containers = [driver, *([executor] * resources.executor_instances)]
    fifths = sum(
        _OVERHEAD_DENOMINATOR * memory + max(_OVERHEAD_DENOMINATOR * _MIN_OVERHEAD_BYTES, _OVERHEAD_NUMERATOR * memory)
        for memory in containers
    )
    cpu = driver_cores + resources.executor_instances * executor_cores
    return {"cpu": str(cpu), "memory": f"{fifths // (_OVERHEAD_DENOMINATOR * _MIB)}Mi"}
