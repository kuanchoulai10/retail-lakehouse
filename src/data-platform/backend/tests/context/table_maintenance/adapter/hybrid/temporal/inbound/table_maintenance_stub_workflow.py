"""Define a stub maintenance workflow that finishes when the test says so."""

from __future__ import annotations

import asyncio

from temporalio import workflow

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
    TableMaintenanceWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
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
        """Keep the workflow input for the started_with query."""
        self._input = input
        self._complete = False

    @workflow.run
    async def run(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        """Wait for complete, then report to the parent; a cancel is reported too unless the plan ignores it."""
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
        """Signal that lets the stub finish."""
        self._complete = True

    @workflow.query
    def started_with(self) -> dict:
        """Query returning the run, table, parent and trigger the workflow started with."""
        return {
            "run_id": self._input.run_id,
            "table_uuid": self._input.table_uuid,
            "parent_workflow_id": self._input.parent_workflow_id,
            "trigger": self._input.trigger,
            "plan": self._input.plan,
        }
