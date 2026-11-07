"""Define a stub maintenance workflow that finishes when the test says so."""

from __future__ import annotations

import asyncio

from temporalio import workflow

from adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
    TableMaintenanceWorkflowInput,
)
from adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationSignal,
)


@workflow.defn(name=TABLE_MAINTENANCE_WORKFLOW)
class TableMaintenanceStubWorkflow:
    """Wait for ``complete``, then signal the parent's current run by workflow id.

    A cancellation is reported to the parent like the real child's cleanup does,
    unless the plan carries ``stub_ignores_cancel``: then the stub keeps waiting.
    """

    @workflow.init
    def __init__(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        self._input = input
        self._complete = False

    @workflow.run
    async def run(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        try:
            await workflow.wait_condition(lambda: self._complete)
        except asyncio.CancelledError:
            if input.plan.get("stub_ignores_cancel"):
                await workflow.wait_condition(lambda: self._complete)
            else:
                await self._report(input)
                raise
        await self._report(input)

    async def _report(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        handle = workflow.get_external_workflow_handle(input.parent_workflow_id)
        await handle.signal(
            TableReconciliationSignal.MAINTENANCE_FINISHED,
            {"run_id": input.run_id, "record_failures": 0},
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
