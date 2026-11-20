"""Define a stub maintenance workflow that finishes when the test says so."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from temporalio import workflow

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TABLE_MAINTENANCE_WORKFLOW,
    RaisePrioritySignal,
    TableMaintenanceSignal,
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
    The priority raises it receives are kept for the ``raises`` query, and a plan carrying
    ``stub_leaves_raises_unapplied`` reports any raise it received as unapplied. A plan carrying
    ``stub_lingers_seconds`` stays open that long after it reported, as the real child does
    while its report activity completes.
    """

    @workflow.init
    def __init__(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        """Keep the workflow input for the started_with query."""
        self._input = input
        self._complete = False
        self._raises: list[str | None] = []

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
        lingers = input.plan.get("stub_lingers_seconds")
        if lingers:
            await workflow.sleep(timedelta(seconds=lingers))

    async def _report(self, input: TableMaintenanceWorkflowInput) -> None:  # noqa: A002
        unapplied = bool(self._raises) and bool(input.plan.get("stub_leaves_raises_unapplied"))
        handle = workflow.get_external_workflow_handle(input.parent_workflow_id)
        await handle.signal(
            TableReconciliationSignal.MAINTENANCE_FINISHED,
            {"run_id": input.run_id, "record_failures": 0, "unapplied_raise": unapplied},
        )

    @workflow.signal(name="complete")
    def complete(self) -> None:
        """Signal that lets the stub finish."""
        self._complete = True

    @workflow.signal(name=TableMaintenanceSignal.RAISE_PRIORITY)
    def raise_priority(self, request: RaisePrioritySignal) -> None:
        """Keep the priority of a raise."""
        self._raises.append(request.priority)

    @workflow.query
    def raises(self) -> list[str | None]:
        """Query returning the priorities of the raises received, in order."""
        return list(self._raises)

    @workflow.query
    def started_with(self) -> dict:
        """Query returning the run, table, parent and trigger the workflow started with."""
        return {
            "run_id": self._input.run_id,
            "table_uuid": self._input.table_uuid,
            "parent_workflow_id": self._input.parent_workflow_id,
            "trigger": self._input.trigger,
            "plan": self._input.plan,
            "attempt_deadline_seconds": self._input.attempt_deadline_seconds,
            "max_attempts": self._input.max_attempts,
            "queue_wait_limit_seconds": self._input.queue_wait_limit_seconds,
        }
