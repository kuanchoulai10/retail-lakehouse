"""Define the CompactionRoundWorkflow."""

from __future__ import annotations

import asyncio
from typing import Any

from temporalio import workflow

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
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.compaction_round_activity_policy import (
    CompactionRoundActivityPolicy,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.mint_workflow_prefixed_id import (
    mint_workflow_prefixed_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows.table_search_attribute_keys import (
    TableSearchAttributeKeys,
)

_POLICY = CompactionRoundActivityPolicy()
_PREFIXED_ROUND_ID_PATCH = "prefixed-compaction-round-id"
_ROUND_ID_PREFIX = "cr"


@workflow.defn(name=COMPACTION_ROUND_WORKFLOW)
class CompactionRoundWorkflow:
    """Run one round of the compaction scheduler and hand its grants to the tables.

    The workflow mints the round's ``cr-`` id once, before its first activity,
    from the workflow's clock and random source (patch
    ``prefixed-compaction-round-id``; a history from before it replays with its
    workflow id as the round id), and every attempt of the schedule activity is
    sent it, so an attempt retried after it saved answers with the round it
    recorded instead of granting twice. The schedule starts each round once (no
    retry policy, no continue-as-new), so one workflow names one round; a reset
    of the workflow would mint a new id. Its current details name the round id
    and what it granted, so the round the console shows can be found in the
    Temporal UI. A
    candidate another writer changed meanwhile makes the activity fail and
    retry on fresh reads. Each granted table's reconciliation is woken once
    with ``compaction_granted``; a table without a running reconciliation is
    skipped (its grant runs out and its candidates are pending again). A round
    that still fails after its retries fails this run; the schedule starts the
    next one.
    """

    @workflow.run
    async def run(self, input: CompactionRoundWorkflowInput) -> dict[str, Any]:  # noqa: A002
        """Schedule the round, signal the granted tables, then tag the workflow with them and return the round.

        The signals go first: tagging can fail the workflow task (an attribute
        the namespace lacks), and the grants must reach their tables anyway.
        """
        round_id = self._mint_round_id()
        result = await workflow.execute_activity(
            CompactionRoundActivity.SCHEDULE_COMPACTION_ROUND,
            {"round_id": round_id, "now": workflow.now().isoformat()},
            start_to_close_timeout=_POLICY.round_timeout,
            retry_policy=_POLICY.retry_policy(),
        )
        granted = [str(table) for table in result["granted_table_uuids"]]
        workflow.set_current_details(compaction_round_details(round_id, int(result["picked"]), len(granted)))
        await asyncio.gather(*(self._grant(table, round_id) for table in granted))
        if granted:
            workflow.upsert_search_attributes([TableSearchAttributeKeys.GRANTED_TABLE_UUIDS.value_set(granted)])
        return result

    @staticmethod
    def _mint_round_id() -> str:
        """Return a new ``cr-`` round id; a history from before prefixed ids replays its workflow id."""
        if not workflow.patched(_PREFIXED_ROUND_ID_PATCH):
            return workflow.info().workflow_id
        return mint_workflow_prefixed_id(_ROUND_ID_PREFIX)

    async def _grant(self, table_uuid: str, round_id: str) -> None:
        await workflow.execute_activity(
            TableMaintenanceActivity.SIGNAL_PARENT,
            {
                "workflow_id": table_reconciliation_workflow_id(table_uuid),
                "signal": TableReconciliationSignal.COMPACTION_GRANTED.value,
                "arg": {"round_id": round_id},
            },
            start_to_close_timeout=_POLICY.signal_timeout,
            retry_policy=_POLICY.retry_policy(),
        )
