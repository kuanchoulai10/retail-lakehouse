"""Test ensure_table_maintenance_admission against a time-skipping Temporal server."""

from __future__ import annotations

import asyncio
import inspect

from temporalio import workflow
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance_admission import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    TableMaintenanceAdmissionWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound import (
    ensure_table_maintenance_admission,
)


@workflow.defn(name=TABLE_MAINTENANCE_ADMISSION_WORKFLOW)
class StubAdmission:
    """Admission workflow stub that records the input it started with."""

    def __init__(self) -> None:
        """Start with no recorded input."""
        self.input: TableMaintenanceAdmissionWorkflowInput | None = None

    @workflow.run
    async def run(self, input: TableMaintenanceAdmissionWorkflowInput) -> None:  # noqa: A002
        """Record the input and wait forever."""
        self.input = input
        await workflow.wait_condition(lambda: False)

    @workflow.query
    def state(self) -> dict:
        """Query returning the limit and lease the workflow started with."""
        assert self.input is not None
        return {"limit": self.input.limit, "lease": self.input.lease_seconds}


async def _scenario() -> tuple[dict, str, str | None]:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        queue = TASK_QUEUE
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[StubAdmission],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            await ensure_table_maintenance_admission(env.client, limit=2, lease_seconds=60)
            await ensure_table_maintenance_admission(env.client, limit=9, lease_seconds=99)
            handle = env.client.get_workflow_handle(TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID)
            state = await handle.query(StubAdmission.state)
            description = await handle.describe()
            summary = await description.static_summary()
            await handle.terminate()
            status = description.status
            return state, status.name if status is not None else "", summary


def test_starts_the_admission_workflow_once_and_keeps_a_running_one():
    """The first call starts the workflow with its limit and summary and a second call keeps the running one."""
    state, status, summary = asyncio.run(_scenario())

    assert state == {"limit": 2, "lease": 60}
    assert status == "RUNNING"
    assert summary == "global Spark maintenance admission (limit=2)"


def test_task_queue_is_the_domain_constant_not_a_parameter():
    """The task queue is a fixed constant and not a parameter of the ensure function."""
    assert "task_queue" not in inspect.signature(ensure_table_maintenance_admission).parameters
