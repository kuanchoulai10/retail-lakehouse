"""Define a stub parent workflow that records maintenance_finished signals."""

from __future__ import annotations

from temporalio import workflow

from adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationSignal,
)


@workflow.defn(name="ParentStub")
class ParentStubWorkflow:
    """Wait forever and record the payloads of finished maintenance runs."""

    def __init__(self) -> None:
        self.finished: list[dict] = []

    @workflow.run
    async def run(self) -> None:
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name=TableReconciliationSignal.MAINTENANCE_FINISHED)
    def maintenance_finished(self, payload: dict) -> None:
        self.finished.append(payload)

    @workflow.query
    def collected(self) -> list[dict]:
        return self.finished
