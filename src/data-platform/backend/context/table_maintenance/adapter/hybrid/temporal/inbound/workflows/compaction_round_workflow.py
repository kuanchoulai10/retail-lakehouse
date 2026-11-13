"""Define the CompactionRoundWorkflow."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

from context.table_maintenance.adapter.hybrid.temporal.contracts.compaction_round import (
    COMPACTION_ROUND_WORKFLOW,
    CompactionRoundActivity,
    CompactionRoundWorkflowInput,
    compaction_round_details,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationSignal,
    table_reconciliation_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_search_attribute_keys import (
    TableSearchAttributeKeys,
)

_ROUND_TIMEOUT = timedelta(minutes=2)
_SIGNAL_TIMEOUT = timedelta(seconds=30)
_ACTIVITY_RETRY = RetryPolicy(maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0)


@workflow.defn(name=COMPACTION_ROUND_WORKFLOW)
class CompactionRoundWorkflow:
    """Run one round of the compaction scheduler and hand its grants to the tables.

    The round is named by the workflow id, so an activity retried after it
    saved answers with the round it recorded instead of granting twice. A
    candidate another writer changed meanwhile makes the activity fail and
    retry on fresh reads. Each granted table's reconciliation is woken once
    with ``compaction_granted``; a table without a running reconciliation is
    skipped (its grant runs out and its candidates are pending again). A round
    that still fails after its retries fails this run; the schedule starts the
    next one.
    """

    @workflow.run
    async def run(self, input: CompactionRoundWorkflowInput) -> dict[str, Any]:  # noqa: A002
        """Schedule the round, tag the workflow with the granted tables, signal them and return the round."""
        round_id = workflow.info().workflow_id
        result = await workflow.execute_activity(
            CompactionRoundActivity.SCHEDULE_COMPACTION_ROUND,
            {"round_id": round_id, "now": workflow.now().isoformat()},
            start_to_close_timeout=_ROUND_TIMEOUT,
            retry_policy=_ACTIVITY_RETRY,
        )
        granted = [str(table) for table in result["granted_table_uuids"]]
        workflow.set_current_details(compaction_round_details(int(result["picked"]), len(granted)))
        if granted:
            workflow.upsert_search_attributes([TableSearchAttributeKeys.GRANTED_TABLE_UUIDS.value_set(granted)])
        await asyncio.gather(*(self._grant(table, round_id) for table in granted))
        return result

    async def _grant(self, table_uuid: str, round_id: str) -> None:
        await workflow.execute_activity(
            TableMaintenanceActivity.SIGNAL_PARENT,
            {
                "workflow_id": table_reconciliation_workflow_id(table_uuid),
                "signal": TableReconciliationSignal.COMPACTION_GRANTED.value,
                "arg": {"round_id": round_id},
            },
            start_to_close_timeout=_SIGNAL_TIMEOUT,
            retry_policy=_ACTIVITY_RETRY,
        )
