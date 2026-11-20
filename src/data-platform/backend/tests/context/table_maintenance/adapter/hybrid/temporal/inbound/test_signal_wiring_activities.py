"""Test the activities that signal or look up other workflows through the Temporal client."""

from __future__ import annotations

import asyncio
import inspect

from temporalio import workflow
from temporalio.testing import ActivityEnvironment, WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationSignal,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    TableMaintenanceActivities,
    TableReconciliationActivities,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_maintenance_activities_with_fakes import (  # noqa: E501
    table_maintenance_activities_with_fakes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_reconciliation_activities_with_fakes import (  # noqa: E501
    table_reconciliation_activities_with_fakes,
)


@workflow.defn(name="StubParent")
class StubParent:
    """Parent workflow stub that records the run ids it is told have finished."""

    def __init__(self) -> None:
        """Start with no finished runs."""
        self.finished: list[str] = []

    @workflow.run
    async def run(self) -> None:
        """Wait forever."""
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name=TableReconciliationSignal.MAINTENANCE_FINISHED)
    def maintenance_finished(self, run_id: str) -> None:
        """Record the run id of a finished maintenance run."""
        self.finished.append(run_id)

    @workflow.query
    def collected(self) -> list[str]:
        """Query returning the recorded run ids."""
        return self.finished


async def _scenario() -> None:
    async with await WorkflowEnvironment.start_local() as env:
        queue = TASK_QUEUE
        activities = table_maintenance_activities_with_fakes(client=env.client)
        lookups = table_reconciliation_activities_with_fakes(client=env.client)
        async with Worker(
            env.client,
            task_queue=queue,
            workflows=[StubParent],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            act_env = ActivityEnvironment()
            parent = await env.client.start_workflow("StubParent", id="parent-1", task_queue=queue)
            delivered = await act_env.run(
                activities.signal_parent,
                {
                    "workflow_id": "parent-1",
                    "signal": TableReconciliationSignal.MAINTENANCE_FINISHED,
                    "arg": "r1",
                },
            )
            assert delivered == {"delivered": True}
            assert await parent.query("collected") == ["r1"]

            missing = await act_env.run(
                activities.signal_parent,
                {
                    "workflow_id": "no-such-parent",
                    "signal": TableReconciliationSignal.MAINTENANCE_FINISHED,
                    "arg": "r1",
                },
            )
            assert missing == {"delivered": False}

            assert await act_env.run(lookups.get_workflow_running, {"workflow_id": "parent-1"}) == {"running": True}
            await parent.terminate()
            assert await act_env.run(lookups.get_workflow_running, {"workflow_id": "parent-1"}) == {"running": False}
            nowhere = {"workflow_id": "no-such-workflow"}
            assert await act_env.run(lookups.get_workflow_running, nowhere) == {"running": False}


def test_signal_parent_and_look_up_a_running_workflow():
    """The parent is signalled when maintenance finishes, and a workflow's running state is looked up."""
    asyncio.run(_scenario())


def test_task_queue_is_the_domain_constant_not_a_parameter():
    """The task queue is a fixed constant and not a parameter of the activities that talk to the client."""
    for activities in (TableMaintenanceActivities, TableReconciliationActivities):
        assert "task_queue" not in inspect.signature(activities.__init__).parameters
