"""Define a stub requester workflow that records admission grant."""

from __future__ import annotations

from temporalio import workflow

from adapter.hybrid.temporal.contracts.table_maintenance import TableMaintenanceSignal


@workflow.defn(name="RequesterStub")
class RequesterStubWorkflow:
    """Wait forever and record every admission grant it receives."""

    def __init__(self) -> None:
        self.grants: list[str] = []

    @workflow.run
    async def run(self) -> None:
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name=TableMaintenanceSignal.ADMISSION_GRANTED)
    def admission_granted(self, request_id: str) -> None:
        self.grants.append(request_id)

    @workflow.query
    def granted(self) -> list[str]:
        return self.grants
