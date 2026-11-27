"""Define the TableDiscoveryRoundWorkflow."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.workflow import ParentClosePolicy

from context.table_maintenance.adapter.hybrid.temporal.contracts.shared import (
    TASK_QUEUE,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery import (
    TABLE_DISCOVERY_WORKFLOW,
    TableDiscoveryWorkflowInput,
    table_discovery_catalog_workflow_id,
    table_discovery_summary,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_discovery_round import (
    TABLE_DISCOVERY_ROUND_WORKFLOW,
    TableDiscoveryRoundActivity,
)

if TYPE_CHECKING:
    import asyncio

_LIST_TIMEOUT = timedelta(minutes=1)
_ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)


@workflow.defn(name=TABLE_DISCOVERY_ROUND_WORKFLOW)
class TableDiscoveryRoundWorkflow:
    """Start one scan of each scanned catalog, and leave them running.

    The one discovery schedule starts a round every interval. Each scan is a child
    ``TableDiscoveryWorkflow`` under the catalog's scan id, abandoned when the round closes, so a
    slow catalog never holds back the next round of the others. A catalog whose scan under that id is
    still going (the previous round's, or one a policy change requested) is skipped this round. A
    failure listing the catalogs, after the activity's retries, fails the round; the next one tries
    again.
    """

    @workflow.run
    async def run(self) -> dict[str, list[str]]:
        """List the scanned catalogs, start a scan of each in order, and return those started and skipped."""
        catalogs: list[str] = await workflow.execute_activity(
            TableDiscoveryRoundActivity.LIST_SCANNED_CATALOGS,
            start_to_close_timeout=_LIST_TIMEOUT,
            retry_policy=_ACTIVITY_RETRY,
        )
        started: list[str] = []
        already_running: list[str] = []
        for catalog in catalogs:
            try:
                scan = await workflow.start_child_workflow(
                    TABLE_DISCOVERY_WORKFLOW,
                    TableDiscoveryWorkflowInput(catalog),
                    id=table_discovery_catalog_workflow_id(catalog),
                    parent_close_policy=ParentClosePolicy.ABANDON,
                    task_queue=TASK_QUEUE,
                    static_summary=table_discovery_summary(catalog, None),
                )
            except WorkflowAlreadyStartedError:
                already_running.append(catalog)
                continue
            scan.add_done_callback(_discard_outcome)
            started.append(catalog)
        return {"started": started, "already_running": already_running}


def _discard_outcome(scan: asyncio.Future[object]) -> None:
    """Read a scan's outcome the round never waits for, so a failed scan is not reported unretrieved."""
    if not scan.cancelled():
        scan.exception()
