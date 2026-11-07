"""Define a stub requester workflow that records admission grant."""

from __future__ import annotations

from temporalio import workflow

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceSignal,
)


@workflow.defn(name="RequesterStub")
class RequesterStubWorkflow:
    """Wait forever and record every admission grant it receives."""

    def __init__(self) -> None:
        """Start with no grants."""
        self.grants: list[str] = []

    @workflow.run
    async def run(self) -> None:
        """Wait forever so the grants can be collected."""
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name=TableMaintenanceSignal.ADMISSION_GRANTED)
    def admission_granted(self, request_id: str) -> None:
        """Collect the request id of an admission grant signal."""
        self.grants.append(request_id)

    @workflow.query
    def granted(self) -> list[str]:
        """Return the collected grant request ids."""
        return self.grants
