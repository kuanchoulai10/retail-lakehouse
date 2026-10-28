"""Test the activities that signal other workflows through the Temporal client."""

from __future__ import annotations

import asyncio
import inspect

from temporalio import workflow
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from adapter.hybrid.temporal.inbound.activities import WorkflowSignalActivities
from adapter.hybrid.temporal.contracts.admission_acquire_signal import (
    AdmissionAcquireSignal,
)
from adapter.hybrid.temporal.contracts.table_maintenance_admission_input import (
    TableMaintenanceAdmissionInput,
)
from adapter.hybrid.temporal.contracts.workflow_names import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW,
)
from adapter.hybrid.temporal.contracts.workflow_ids import (
    TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID,
    SIGNAL_MAINTENANCE_FINISHED,
    TASK_QUEUE,
)


@workflow.defn(name=TABLE_MAINTENANCE_ADMISSION_WORKFLOW)
class StubAdmission:
    def __init__(self) -> None:
        self.acquires: list[AdmissionAcquireSignal] = []
        self.input: TableMaintenanceAdmissionInput | None = None

    @workflow.run
    async def run(self, input: TableMaintenanceAdmissionInput) -> None:
        self.input = input
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name="acquire")
    def acquire(self, signal: AdmissionAcquireSignal) -> None:
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
    # The time-skipping server drops the summary of a signal-with-start.
    async with await WorkflowEnvironment.start_local() as env:
        queue = TASK_QUEUE
        activities = WorkflowSignalActivities(
            env.client, admission_limit=2, admission_lease_seconds=60
        )
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[StubAdmission, StubParent],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            act_env = ActivityEnvironment()
            for request_id in ("a", "b"):
                await act_env.run(
                    activities.signal_admission_acquire,
                    {"request_id": request_id, "requester_workflow_id": "w"},
                )
            admission = env.client.get_workflow_handle(
                TABLE_MAINTENANCE_ADMISSION_WORKFLOW_ID
            )
            state = await admission.query("state")
            assert state == {"limit": 2, "lease": 60, "acquires": ["a", "b"]}
            description = await admission.describe()
            assert await description.static_summary() == (
                "global Spark maintenance admission (limit=2)"
            )

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


def test_signal_with_start_admission_once_and_signal_parent():
    asyncio.run(_scenario())


def test_task_queue_is_the_domain_constant_not_a_parameter():
    parameters = inspect.signature(WorkflowSignalActivities.__init__).parameters
    assert "task_queue" not in parameters
