"""Test SendMaintenanceResultTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time

import pytest

from context.table_maintenance.adapter.hybrid.temporal.outbound.table_maintenance_run import (
    SendMaintenanceResultTemporalGateway,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
)
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.outbound.table_maintenance_run import (
    SendMaintenanceResultGatewayInput,
)


def _input(run_id: str, workflow_id: str) -> SendMaintenanceResultGatewayInput:
    return SendMaintenanceResultGatewayInput(
        execution_ref=workflow_id,
        run_id=run_id,
        operation="rewrite_data_files",
        attempt=1,
        succeeded=True,
        metrics={"rewritten": 3},
        error=None,
    )


def test_result_reaches_maintenance_workflow(harness):
    async def start() -> None:
        await harness.client.start_workflow(
            TABLE_MAINTENANCE_WORKFLOW,
            {},
            id="any-workflow-id-of-r1",
            task_queue=TASK_QUEUE,
        )

    harness.bridge.run(start)
    SendMaintenanceResultTemporalGateway(harness.client, harness.bridge).send(_input("r1", "any-workflow-id-of-r1"))
    handle = harness.client.get_workflow_handle("any-workflow-id-of-r1")

    async def query() -> list:
        return await handle.query("collected")

    got: list = []
    deadline = time.time() + 5
    while not got and time.time() < deadline:
        got = harness.bridge.run(query)
        time.sleep(0.2)
    assert got == [
        {
            "run_id": "r1",
            "operation": "rewrite_data_files",
            "attempt": 1,
            "succeeded": True,
            "metrics": {"rewritten": 3},
            "error": None,
        }
    ]


def test_result_for_missing_workflow_raises_not_found(harness):
    gateway = SendMaintenanceResultTemporalGateway(harness.client, harness.bridge)
    with pytest.raises(NotFoundError):
        gateway.send(_input("nope", "missing-workflow"))
