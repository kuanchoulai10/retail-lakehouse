"""Test the resources of the PodGroup of a maintenance SparkApplication."""

from __future__ import annotations

import pytest

from context.table_maintenance.adapter.outbound.table_maintenance_run.k8s import (
    SparkSizeResources,
    pod_group_resources,
)


@pytest.mark.parametrize(
    ("driver", "executor", "memory"),
    [("768m", "768m", "2304Mi"), ("1g", "1536m", "3584Mi"), ("1536m", "2g", "5017Mi")],
)
def test_pod_group_resources_of_the_chart_sizes(driver: str, executor: str, memory: str):
    """The chart's S, M and L sizes need two cores and the memory Volcano is asked to hold for them."""
    got = pod_group_resources(SparkSizeResources(driver, executor, 1), driver_cores=1, executor_cores=1)

    assert got == {"cpu": "2", "memory": memory}


def test_two_executors_count_twice():
    """Each executor adds its cores and its memory with overhead."""
    got = pod_group_resources(SparkSizeResources("768m", "768m", 2), driver_cores=1, executor_cores=1)

    assert got == {"cpu": "3", "memory": "3456Mi"}


def test_executor_cores_multiply_by_the_executor_count():
    """The cpu is the driver's cores plus the cores of every executor."""
    got = pod_group_resources(SparkSizeResources("768m", "768m", 3), driver_cores=2, executor_cores=4)

    assert got["cpu"] == "14"


def test_g_and_m_agree():
    """One GiB and 1024 MiB ask for the same memory."""
    in_g = pod_group_resources(SparkSizeResources("1g", "1g", 1), driver_cores=1, executor_cores=1)
    in_m = pod_group_resources(SparkSizeResources("1024m", "1024m", 1), driver_cores=1, executor_cores=1)

    assert in_g == in_m


def test_unknown_unit_is_refused():
    """A memory string Spark would not read is refused."""
    with pytest.raises(ValueError, match="memory"):
        pod_group_resources(SparkSizeResources("1x", "768m", 1), driver_cores=1, executor_cores=1)
