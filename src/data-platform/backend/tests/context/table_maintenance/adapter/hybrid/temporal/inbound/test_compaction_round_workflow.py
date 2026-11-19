"""Test the CompactionRoundWorkflow on a time-skipping Temporal test server."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest
from temporalio import activity
from temporalio.client import WorkflowFailureError, WorkflowHistory
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

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
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import CompactionRoundActivities
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    CompactionRoundWorkflow,
    TableSearchAttributeKeys,
)
from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.compaction_round import CompactionRoundId, PriorityWeights
from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.service.compaction_round import ScheduleCompactionRoundService
from shared_kernel import prefixed_id_pattern
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.register_table_search_attributes import (
    register_table_search_attributes,
)
from tests.context.table_maintenance.adapter.hybrid.temporal.inbound.table_maintenance_activities_with_fakes import (  # noqa: E501
    table_maintenance_activities_with_fakes,
)
from tests.context.table_maintenance.fakes.in_memory_compaction_candidates_repo import (
    InMemoryCompactionCandidatesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_compaction_rounds_repo import InMemoryCompactionRoundsRepo
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.port.inbound.compaction_round import ScheduleCompactionRoundUseCase

ROUND_ID_SHAPE = prefixed_id_pattern("cr")


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
    history: WorkflowHistory


@dataclass
class Script:
    """Answer the round activity and, unless ``real_signals``, record the signals instead of sending them.

    With a ``schedule`` use case the round activity runs it, as the worker does, instead of answering ``answer``.
    """

    answer: dict[str, Any]
    real_signals: bool = False
    fail: bool = False
    schedule: ScheduleCompactionRoundUseCase | None = None
    requests: list[dict[str, Any]] = field(default_factory=list)
    signals: list[dict[str, Any]] = field(default_factory=list)


def _listed(values: Sequence[str] | None) -> list[str] | None:
    return None if values is None else list(values)


def _run(script: Script, *, max_cached_workflows: int = 1000) -> Outcome:
    @activity.defn(name=CompactionRoundActivity.SCHEDULE_COMPACTION_ROUND)
    async def schedule_compaction_round(request: dict[str, Any]) -> dict[str, Any]:
        script.requests.append(request)
        if script.fail:
            raise ApplicationError("database down", non_retryable=True)
        if script.schedule is not None:
            return CompactionRoundActivities(schedule=script.schedule).schedule_compaction_round(request)
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
                max_cached_workflows=max_cached_workflows,
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
                    history=await handle.fetch_history(),
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


def test_round_workflow_passes_a_cr_id():
    """The workflow mints a ``cr-`` round id, not its workflow id, and runs the round at workflow time."""
    outcome = _run(Script(_round("t-1")))

    request = outcome.requests[0]
    assert ROUND_ID_SHAPE.fullmatch(request["round_id"])
    assert outcome.signals[0]["arg"] == {"round_id": request["round_id"]}
    assert datetime.fromisoformat(request["now"]).tzinfo is not None


NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)


def _table(table_uuid: str) -> Table:
    return Table.register(
        TableId(table_uuid),
        TableName(catalog="iceberg", namespace="retail", table=table_uuid),
        TableDiscoveryRuleId.new(),
        NOW,
    )


def _candidate(table: str, value: str) -> CompactionCandidate:
    return CompactionCandidate.create(
        table_uuid=TableId(table),
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"day={value}",
        score=CandidateScore(reducible_files=5, data_bytes=1000, estimated_gb_hours=0.02, score=0.9),
        last_written_at=None,
        hold_reason=None,
        now=NOW - timedelta(minutes=5),
    )


def _rounds_repo_failing_its_first_save(monkeypatch: pytest.MonkeyPatch) -> InMemoryCompactionRoundsRepo:
    """Fail the first save of a round, as a crash between the grants and the record would."""
    rounds = InMemoryCompactionRoundsRepo()
    save = rounds.save
    saves: list[object] = []

    def fail_first(entity) -> None:  # noqa: ANN001
        saves.append(entity)
        if len(saves) == 1:
            raise RuntimeError("the database went away")
        save(entity)

    monkeypatch.setattr(rounds, "save", fail_first)
    return rounds


def test_round_id_is_stable_across_activity_retries(monkeypatch: pytest.MonkeyPatch):
    """A schedule activity retried after it saved its grants gets the same ``cr-`` id, so it finds and records them.

    The first attempt grants both candidates and fails before recording the
    round; the retry is sent the same payload, finds the grants under its
    round id and records exactly them instead of granting a second batch.
    """
    tables = InMemoryTablesRepo()
    for table in ("t-1", "t-2"):
        tables.create(_table(table))
    candidates = InMemoryCompactionCandidatesRepo()
    candidates.save_all([_candidate("t-1", "a"), _candidate("t-2", "b")])
    rounds = _rounds_repo_failing_its_first_save(monkeypatch)
    service = ScheduleCompactionRoundService(
        candidates,
        rounds,
        tables,
        weights=PriorityWeights(),
        budget_gb_hours=1,
        partitions_per_run=10,
        sla={priority: timedelta(hours=1) for priority in MaintenancePriority},
        grant_lease=timedelta(minutes=10),
        rounds_kept=500,
    )

    outcome = _run(Script(_round(), schedule=service))

    first, retry = outcome.requests
    assert retry == first
    round_id = first["round_id"]
    assert ROUND_ID_SHAPE.fullmatch(round_id)
    assert rounds.get(CompactionRoundId(round_id)) is not None
    assert {(c.state, c.granted_round_id) for c in candidates.list_all()} == {(CandidateState.GRANTED, round_id)}
    assert (outcome.result["round_id"], outcome.result["picked"]) == (round_id, 2)


def test_round_id_survives_replay():
    """The round id is minted deterministically: with no workflow cached, every later task replays the minting.

    The signals are scheduled in a later workflow task than the minting, so
    they carry the id minted again on replay; it agrees with the one the round
    activity got, the history carries the patch marker that keeps older
    histories on their workflow id, and it replays cleanly under the sandbox.
    """
    outcome = _run(Script(_round("t-1", "t-2")), max_cached_workflows=0)

    round_id = outcome.requests[0]["round_id"]
    assert ROUND_ID_SHAPE.fullmatch(round_id)
    assert {signal["arg"]["round_id"] for signal in outcome.signals} == {round_id}
    markers = [e.SerializeToString() for e in outcome.history.events if e.HasField("marker_recorded_event_attributes")]
    assert any(b"prefixed-compaction-round-id" in m for m in markers)
    asyncio.run(Replayer(workflows=[CompactionRoundWorkflow]).replay_workflow(outcome.history))


def test_round_tags_itself_with_the_tables_it_granted():
    """The round upserts GrantedTableUuids, so a table's rounds can be found in the Temporal UI."""
    outcome = _run(Script(_round("t-1", "t-2", picked=3)))

    assert outcome.granted == ["t-1", "t-2"]
    assert outcome.details == f"round {outcome.requests[0]['round_id']} · granted 3 partitions of 2 tables"


def test_round_with_nothing_granted_signals_nobody():
    """A round that granted nothing sends no signal and sets no granted tables."""
    outcome = _run(Script(_round()))

    assert outcome.signals == []
    assert outcome.granted is None
    assert outcome.details == f"round {outcome.requests[0]['round_id']} · granted 0 partitions of 0 tables"


def test_a_missing_reconciliation_workflow_does_not_fail_the_round():
    """A granted table without a running reconciliation is skipped; its grant runs out and it is pending again."""
    outcome = _run(Script(_round("t-gone"), real_signals=True))

    assert outcome.result["granted_table_uuids"] == ["t-gone"]


def test_a_failed_round_fails_the_workflow():
    """A round activity that gives up fails this run; the schedule starts the next one."""
    with pytest.raises(WorkflowFailureError):
        _run(Script(_round(), fail=True))
