"""Define the TableDiscoveryWorkflow."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

from adapter.temporal_contracts.activity_names import SYNC_DISCOVERED_TABLES
from adapter.temporal_contracts.table_discovery_workflow_input import (
    TableDiscoveryWorkflowInput,
)
from adapter.temporal_contracts.workflow_names import TABLE_DISCOVERY_WORKFLOW

_SYNC_TIMEOUT = timedelta(minutes=10)
_ACTIVITY_RETRY = RetryPolicy(
    maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0
)


@workflow.defn(name=TABLE_DISCOVERY_WORKFLOW)
class TableDiscoveryWorkflow:
    """Synchronise the table registry with one catalog or namespace.

    A failure after the activity's retries fails this run; the schedule starts
    the next one.
    """

    @workflow.run
    async def run(self, input: TableDiscoveryWorkflowInput) -> dict[str, Any]:  # noqa: A002
        """Run ``sync_discovered_tables`` and return its output."""
        return await workflow.execute_activity(
            SYNC_DISCOVERED_TABLES,
            {"catalog": input.catalog, "namespace": input.namespace},
            start_to_close_timeout=_SYNC_TIMEOUT,
            retry_policy=_ACTIVITY_RETRY,
        )
