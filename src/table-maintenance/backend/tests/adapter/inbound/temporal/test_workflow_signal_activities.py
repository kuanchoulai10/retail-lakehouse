"""Test the activities that signal other workflows through the Temporal client."""

from __future__ import annotations

import asyncio
import uuid

from temporalio import workflow
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from adapter.inbound.temporal.activities import WorkflowSignalActivities
from adapter.temporal_contracts.capacity_acquire_signal import CapacityAcquireSignal
from adapter.temporal_contracts.capacity_limiter_input import CapacityLimiterInput
from adapter.temporal_contracts.workflow_names import CAPACITY_LIMITER_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    CAPACITY_WORKFLOW_ID,
    SIGNAL_MAINTENANCE_FINISHED,
)


@workflow.defn(name=CAPACITY_LIMITER_WORKFLOW)
class StubLimiter:
    def __init__(self) -> None:
        self.acquires: list[CapacityAcquireSignal] = []
        self.input: CapacityLimiterInput | None = None

    @workflow.run
    async def run(self, input: CapacityLimiterInput) -> None:
        self.input = input
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name="acquire")
    def acquire(self, signal: CapacityAcquireSignal) -> None:
        self.acquires.append(signal)

    @workflow.query
    def state(self) -> dict:
        assert self.input is not None
        return {
            "limit": self.input.limit,
            "lease": self.input.lease_seconds,
            "acquires": [a.request_id for a in self.acquires],
        }


@workflow.defn(name="StubParent")
class StubParent:
    def __init__(self) -> None:
        self.finished: list[str] = []

    @workflow.run
    async def run(self) -> None:
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name=SIGNAL_MAINTENANCE_FINISHED)
    def maintenance_finished(self, run_id: str) -> None:
        self.finished.append(run_id)

    @workflow.query
    def collected(self) -> list[str]:
        return self.finished


async def _scenario() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as env:
        queue = f"q-{uuid.uuid4()}"
        activities = WorkflowSignalActivities(
            env.client, capacity_limit=2, capacity_lease_seconds=60, task_queue=queue
        )
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[StubLimiter, StubParent],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            act_env = ActivityEnvironment()
            for request_id in ("a", "b"):
                await act_env.run(
                    activities.signal_capacity_acquire,
                    {"request_id": request_id, "requester_workflow_id": "w"},
                )
            limiter = env.client.get_workflow_handle(CAPACITY_WORKFLOW_ID)
            state = await limiter.query("state")
            assert state == {"limit": 2, "lease": 60, "acquires": ["a", "b"]}

            parent = await env.client.start_workflow(
                "StubParent", id="parent-1", task_queue=queue
            )
            delivered = await act_env.run(
                activities.signal_parent,
                {
                    "workflow_id": "parent-1",
                    "signal": SIGNAL_MAINTENANCE_FINISHED,
                    "arg": "r1",
                },
            )
            assert delivered == {"delivered": True}
            assert await parent.query("collected") == ["r1"]

            missing = await act_env.run(
                activities.signal_parent,
                {
                    "workflow_id": "no-such-parent",
                    "signal": SIGNAL_MAINTENANCE_FINISHED,
                    "arg": "r1",
                },
            )
            assert missing == {"delivered": False}


def test_signal_with_start_limiter_once_and_signal_parent():
    asyncio.run(_scenario())
