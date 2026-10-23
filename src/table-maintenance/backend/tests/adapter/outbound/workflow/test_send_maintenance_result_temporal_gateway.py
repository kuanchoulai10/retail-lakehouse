"""Test SendMaintenanceResultTemporalGateway against a local Temporal server."""

from __future__ import annotations

import time

import pytest

from adapter.outbound.workflow.temporal.send_maintenance_result_temporal_gateway import (
    SendMaintenanceResultTemporalGateway,
)
from adapter.temporal_contracts.workflow_names import MAINTENANCE_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    TASK_QUEUE,
    maintenance_workflow_id,
)
from application.exceptions import NotFoundError
from application.port.outbound.workflow.send_maintenance_result import (
    SendMaintenanceResultGatewayInput,
)


def _input(run_id: str) -> SendMaintenanceResultGatewayInput:
    return SendMaintenanceResultGatewayInput(
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
            MAINTENANCE_WORKFLOW,
            {},
            id=maintenance_workflow_id("r1"),
            task_queue=TASK_QUEUE,
        )

    harness.bridge.run(start)
    SendMaintenanceResultTemporalGateway(harness.client, harness.bridge).send(
        _input("r1")
    )
    handle = harness.client.get_workflow_handle(maintenance_workflow_id("r1"))

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
        gateway.send(_input("nope"))
