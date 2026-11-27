"""Define a stub catalog scan that finishes when the test says so."""

from __future__ import annotations

from temporalio import workflow
from temporalio.exceptions import ApplicationError

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryWorkflowInput,
)

FAILING_CATALOG = "broken"


@workflow.defn(name=TABLE_DISCOVERY_WORKFLOW)
class TableDiscoveryStubWorkflow:
    """Scan nothing: fail at once for the catalog ``broken``, else wait for ``finish`` and return the scope."""

    def __init__(self) -> None:
        """Start unfinished."""
        self._finished = False

    @workflow.run
    async def run(self, input: TableDiscoveryWorkflowInput) -> dict[str, str | None]:  # noqa: A002
        """Fail for the failing catalog; otherwise wait for ``finish``, then return the scope it was given."""
        if input.catalog == FAILING_CATALOG:
            raise ApplicationError("catalog down", non_retryable=True)
        await workflow.wait_condition(lambda: self._finished)
        return {"catalog": input.catalog, "namespace": input.namespace}

    @workflow.signal(name="finish")
    def finish(self) -> None:
        """Let the scan return."""
        self._finished = True
