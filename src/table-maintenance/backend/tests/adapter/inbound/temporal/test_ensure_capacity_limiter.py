"""Test ensure_capacity_limiter against a time-skipping Temporal server."""

from __future__ import annotations

import asyncio
import uuid

from temporalio import workflow
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from adapter.inbound.temporal.ensure_capacity_limiter import ensure_capacity_limiter
from adapter.temporal_contracts.capacity_limiter_input import CapacityLimiterInput
from adapter.temporal_contracts.workflow_names import CAPACITY_LIMITER_WORKFLOW
from application.domain.model.maintenance.workflow_ids import CAPACITY_WORKFLOW_ID


@workflow.defn(name=CAPACITY_LIMITER_WORKFLOW)
class StubLimiter:
    def __init__(self) -> None:
        self.input: CapacityLimiterInput | None = None

    @workflow.run
    async def run(self, input: CapacityLimiterInput) -> None:  # noqa: A002
        self.input = input
        await workflow.wait_condition(lambda: False)

    @workflow.query
    def state(self) -> dict:
        assert self.input is not None
        return {"limit": self.input.limit, "lease": self.input.lease_seconds}


async def _scenario() -> tuple[dict, str]:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        queue = f"q-{uuid.uuid4()}"
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[StubLimiter],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            await ensure_capacity_limiter(
                env.client, limit=2, lease_seconds=60, task_queue=queue
            )
            await ensure_capacity_limiter(
                env.client, limit=9, lease_seconds=99, task_queue=queue
            )
            handle = env.client.get_workflow_handle(CAPACITY_WORKFLOW_ID)
            state = await handle.query(StubLimiter.state)
            description = await handle.describe()
            await handle.terminate()
            status = description.status
            return state, status.name if status is not None else ""


def test_starts_the_limiter_once_and_keeps_a_running_one():
    state, status = asyncio.run(_scenario())

    assert state == {"limit": 2, "lease": 60}
    assert status == "RUNNING"
