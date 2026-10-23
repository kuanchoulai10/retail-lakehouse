"""Define a stub parent workflow that records maintenance_finished signals."""

from __future__ import annotations

from temporalio import workflow

from application.domain.model.maintenance.workflow_ids import (
    SIGNAL_MAINTENANCE_FINISHED,
)


@workflow.defn(name="ParentStub")
class ParentStubWorkflow:
    """Wait forever and record the run ids of finished maintenance runs."""

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
