"""Test the CompactionRoundWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from context.table_maintenance.adapter.hybrid.temporal.contracts.compaction_round import (
    COMPACTION_ROUND_WORKFLOW,
    CompactionRoundActivity,
    CompactionRoundWorkflowInput,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationSignal,
    table_reconciliation_workflow_id,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    CompactionRoundWorkflow,
    TableSearchAttributeKeys,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.register_table_search_attributes import (
    register_table_search_attributes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_maintenance_activities_with_fakes import (  # noqa: E501
    table_maintenance_activities_with_fakes,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


def _round(*tables: str, picked: int | None = None) -> dict[str, Any]:
    return {
        "round_id": "set-by-the-activity",
        "granted_table_uuids": list(tables),
        "picked": len(tables) if picked is None else picked,
        "skipped_total": 4,
        "used_gb_hours": 0.04,
        "budget_gb_hours": 0.05,
    }


@dataclass
class Outcome:
    """What one round did: its result, the round requests, the signals sent and its search attributes."""

    result: dict[str, Any]
    requests: list[dict[str, Any]]
    signals: list[dict[str, Any]]
    granted: list[str] | None
    details: str


@dataclass
class Script:
    """Answer the round activity and, unless ``real_signals``, record the signals instead of sending them."""

    answer: dict[str, Any]
    real_signals: bool = False
    fail: bool = False
    requests: list[dict[str, Any]] = field(default_factory=list)
    signals: list[dict[str, Any]] = field(default_factory=list)


def _listed(values: Sequence[str] | None) -> list[str] | None:
    return None if values is None else list(values)


def _run(script: Script) -> Outcome:
    @activity.defn(name=CompactionRoundActivity.SCHEDULE_COMPACTION_ROUND)
    async def schedule_compaction_round(request: dict[str, Any]) -> dict[str, Any]:
        script.requests.append(request)
        if script.fail:
            raise ApplicationError("database down", non_retryable=True)
        return {**script.answer, "round_id": request["round_id"]}

    @activity.defn(name=TableMaintenanceActivity.SIGNAL_PARENT)
    async def signal_parent(request: dict[str, Any]) -> dict[str, bool]:
        script.signals.append(request)
        return {"delivered": True}

    async def go() -> Outcome:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            await register_table_search_attributes(env.client)
            queue = f"q-{uuid.uuid4()}"
            real = table_maintenance_activities_with_fakes(client=env.client)
            async with Worker(
                env.client,
                task_queue=queue,
                workflows=[CompactionRoundWorkflow],
                activities=[schedule_compaction_round, real.signal_parent if script.real_signals else signal_parent],
            ):
                handle = await env.client.start_workflow(
                    COMPACTION_ROUND_WORKFLOW,
                    CompactionRoundWorkflowInput(),
                    id=f"compaction-rounds-{uuid.uuid4()}",
                    task_queue=queue,
                )
                result = await asyncio.wait_for(handle.result(), timeout=20)
                description = await handle.describe()
                metadata = await handle.query("__temporal_workflow_metadata")
                return Outcome(
                    result=result,
                    requests=script.requests,
                    signals=script.signals,
                    granted=_listed(
                        description.typed_search_attributes.get(TableSearchAttributeKeys.GRANTED_TABLE_UUIDS)
                    ),
                    details=metadata.current_details,
                )

    return asyncio.run(go())


def test_round_signals_each_granted_table_once():
    """Each table the round granted is woken once with the round's id."""
    outcome = _run(Script(_round("t-1", "t-2", picked=3)))

    round_id = outcome.requests[0]["round_id"]
    assert sorted(outcome.signals, key=lambda s: s["workflow_id"]) == [
        {
            "workflow_id": table_reconciliation_workflow_id(table),
            "signal": TableReconciliationSignal.COMPACTION_GRANTED.value,
            "arg": {"round_id": round_id},
        }
        for table in ("t-1", "t-2")
    ]
    assert outcome.result == {**_round("t-1", "t-2", picked=3), "round_id": round_id}


def test_round_is_named_by_its_workflow_and_runs_at_workflow_time():
    """The round id is the workflow id, so a retried activity records the same round; now is workflow time."""
    outcome = _run(Script(_round()))

    request = outcome.requests[0]
    assert request["round_id"].startswith("compaction-rounds-")
    assert datetime.fromisoformat(request["now"]).tzinfo is not None


def test_round_tags_itself_with_the_tables_it_granted():
    """The round upserts GrantedTableUuids, so a table's rounds can be found in the Temporal UI."""
    outcome = _run(Script(_round("t-1", "t-2", picked=3)))

    assert outcome.granted == ["t-1", "t-2"]
    assert outcome.details == "granted 3 partitions of 2 tables"


def test_round_with_nothing_granted_signals_nobody():
    """A round that granted nothing sends no signal and sets no granted tables."""
    outcome = _run(Script(_round()))

    assert outcome.signals == []
    assert outcome.granted is None
    assert outcome.details == "granted 0 partitions of 0 tables"


def test_a_missing_reconciliation_workflow_does_not_fail_the_round():
    """A granted table without a running reconciliation is skipped; its grant runs out and it is pending again."""
    outcome = _run(Script(_round("t-gone"), real_signals=True))

    assert outcome.result["granted_table_uuids"] == ["t-gone"]


def test_a_failed_round_fails_the_workflow():
    """A round activity that gives up fails this run; the schedule starts the next one."""
    with pytest.raises(WorkflowFailureError):
        _run(Script(_round(), fail=True))
