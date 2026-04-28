"""Tests for SubmitJobRunGatewayInput value object."""

import pytest

from application.port.outbound.job_run.submit_job_run.input import (
    SubmitJobRunGatewayInput,
)


def test_stores_fields():
    """Verify all fields are stored correctly."""
    sub = SubmitJobRunGatewayInput(
        run_id="r1",
        job_id="j1",
        job_type="expire_snapshots",
        catalog="retail",
        table="inventory.orders",
        job_config={"retain_last": 5},
        driver_memory="2g",
        executor_memory="4g",
        executor_instances=3,
        cron_expression="0 2 * * *",
    )
    assert sub.run_id == "r1"
    assert sub.job_id == "j1"
    assert sub.job_type == "expire_snapshots"
    assert sub.catalog == "retail"
    assert sub.table == "inventory.orders"
    assert sub.job_config == {"retain_last": 5}
    assert sub.driver_memory == "2g"
    assert sub.executor_memory == "4g"
    assert sub.executor_instances == 3
    assert sub.cron_expression == "0 2 * * *"


def test_cron_expression_none():
    """Verify cron_expression can be None."""
    sub = SubmitJobRunGatewayInput(
        run_id="r1",
        job_id="j1",
        job_type="expire_snapshots",
        catalog="retail",
        table="orders",
        job_config={},
        driver_memory="512m",
        executor_memory="1g",
        executor_instances=1,
        cron_expression=None,
    )
    assert sub.cron_expression is None


def test_is_frozen():
    """Verify SubmitJobRunGatewayInput is immutable."""
    sub = SubmitJobRunGatewayInput(
        run_id="r1",
        job_id="j1",
        job_type="expire_snapshots",
        catalog="retail",
        table="orders",
        job_config={},
        driver_memory="512m",
        executor_memory="1g",
        executor_instances=1,
        cron_expression=None,
    )
    with pytest.raises(AttributeError):
        sub.run_id = "other"  # type: ignore[misc]  # ty: ignore[invalid-assignment]
