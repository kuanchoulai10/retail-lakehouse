"""Define a stub maintenance workflow that finishes when the test says so."""

from __future__ import annotations

from temporalio import workflow

from adapter.temporal_contracts.maintenance_workflow_input import (
    MaintenanceWorkflowInput,
)
from adapter.temporal_contracts.workflow_names import MAINTENANCE_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    SIGNAL_MAINTENANCE_FINISHED,
)


@workflow.defn(name=MAINTENANCE_WORKFLOW)
class MaintenanceStubWorkflow:
    """Wait for ``complete``, then signal the parent's current run by workflow id."""

    @workflow.init
    def __init__(self, input: MaintenanceWorkflowInput) -> None:  # noqa: A002
        self._input = input
        self._complete = False

    @workflow.run
    async def run(self, input: MaintenanceWorkflowInput) -> None:  # noqa: A002
        await workflow.wait_condition(lambda: self._complete)
        handle = workflow.get_external_workflow_handle(input.parent_workflow_id)
        await handle.signal(
            SIGNAL_MAINTENANCE_FINISHED, {"run_id": input.run_id, "record_failures": 0}
        )

    @workflow.signal(name="complete")
    def complete(self) -> None:
        self._complete = True

    @workflow.query
    def started_with(self) -> dict:
        return {
            "run_id": self._input.run_id,
            "table_uuid": self._input.table_uuid,
            "parent_workflow_id": self._input.parent_workflow_id,
            "trigger": self._input.trigger,
            "plan": self._input.plan,
        }
