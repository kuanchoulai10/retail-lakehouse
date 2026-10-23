"""Define a stub requester workflow that records capacity grants."""

from __future__ import annotations

from temporalio import workflow

from application.domain.model.maintenance.workflow_ids import SIGNAL_CAPACITY_GRANTED


@workflow.defn(name="RequesterStub")
class RequesterStubWorkflow:
    """Wait forever and record every capacity grant it receives."""

    def __init__(self) -> None:
        self.grants: list[str] = []

    @workflow.run
    async def run(self) -> None:
        await workflow.wait_condition(lambda: False)

    @workflow.signal(name=SIGNAL_CAPACITY_GRANTED)
    def capacity_granted(self, request_id: str) -> None:
        self.grants.append(request_id)

    @workflow.query
    def granted(self) -> list[str]:
        return self.grants
