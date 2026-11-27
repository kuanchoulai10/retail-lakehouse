"""Define the TableDiscoveryWorkflow."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryActivity,
    TableDiscoverySignal,
    TableDiscoveryWorkflowInput,
)

_SYNC_TIMEOUT = timedelta(minutes=10)
_ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)


@workflow.defn(name=TABLE_DISCOVERY_WORKFLOW)
class TableDiscoveryWorkflow:
    """Synchronise the table registry with one catalog or namespace.

    A scan reads the discovery policies when its sync starts, so a rescan requested while it runs
    (``request_rescan``, sent by signal-with-start after a policy change of its catalog) runs the
    scan once more, as a new run of the same id through continue-as-new. Requests fold into one
    pending flag, cleared as each run starts: a request that started the run, or arrived before it
    began, is served by that run. A failure after the activity's retries fails this run, a pending
    rescan with it; the next round starts the next scan.
    """

    def __init__(self) -> None:
        """Start with no rescan pending."""
        self._rescan_requested = False

    @workflow.run
    async def run(self, input: TableDiscoveryWorkflowInput) -> dict[str, Any]:  # noqa: A002
        """Run ``sync_discovered_tables`` and return its output, or scan again if a rescan was requested meanwhile."""
        self._rescan_requested = False
        output = await workflow.execute_activity(
            TableDiscoveryActivity.SYNC_DISCOVERED_TABLES,
            {"catalog": input.catalog, "namespace": input.namespace},
            start_to_close_timeout=_SYNC_TIMEOUT,
            retry_policy=_ACTIVITY_RETRY,
        )
        if self._rescan_requested:
            workflow.continue_as_new(input)
        return output

    @workflow.signal(name=TableDiscoverySignal.REQUEST_RESCAN)
    def request_rescan(self) -> None:
        """Ask for one more scan once the one running finishes."""
        self._rescan_requested = True
