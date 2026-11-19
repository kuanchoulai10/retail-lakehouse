"""Test the CompactionRoundActivities."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from temporalio.exceptions import ApplicationError

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities import (
    CompactionRoundActivities,
)
from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CompactionCandidate,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.compaction_round import PriorityWeights
from context.table_maintenance.application.domain.model.table import Table, TableId, TableName
from context.table_maintenance.application.domain.model.table_discovery_rules import TableDiscoveryRuleId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.port.inbound.compaction_round import (
    ScheduleCompactionRoundUseCase,
    ScheduleCompactionRoundUseCaseInput,
    ScheduleCompactionRoundUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.compaction_candidate import (
    StaleCompactionCandidate,
)
from context.table_maintenance.application.service.compaction_round import ScheduleCompactionRoundService
from tests.context.table_maintenance.fakes.in_memory_compaction_candidates_repo import (
    InMemoryCompactionCandidatesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_compaction_rounds_repo import InMemoryCompactionRoundsRepo
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
WORKFLOW_ROUND_ID = "cr-01kaa4zc9qf3v8d2m6xk0w7b2r"
WORKFLOW_SCHEDULE_REQUEST = {"round_id": WORKFLOW_ROUND_ID, "now": "2026-11-13T12:00:00+00:00"}


class FakeSchedule(ScheduleCompactionRoundUseCase):
    """Record each round request and answer a fixed round, or raise."""

    def __init__(self, error: Exception | None = None) -> None:
        """Start with no requests."""
        self.requests: list[ScheduleCompactionRoundUseCaseInput] = []
        self._error = error

    def execute(self, request: ScheduleCompactionRoundUseCaseInput) -> ScheduleCompactionRoundUseCaseOutput:
        """Record the request and answer the round, or raise the configured error."""
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        return ScheduleCompactionRoundUseCaseOutput(
            round_id=request.round_id,
            granted_table_uuids=("t-1",),
            picked=2,
            skipped_total=1,
            used_gb_hours=0.04,
            budget_gb_hours=0.05,
        )


def test_schedule_passes_the_round_and_now_and_returns_dict():
    """The activity runs the round named by the workflow at the workflow's now and returns its output."""
    schedule = FakeSchedule()

    result = CompactionRoundActivities(schedule=schedule).schedule_compaction_round(
        {"round_id": WORKFLOW_ROUND_ID, "now": NOW.isoformat()}
    )

    assert schedule.requests == [ScheduleCompactionRoundUseCaseInput(round_id=WORKFLOW_ROUND_ID, now=NOW)]
    assert result == {
        "round_id": WORKFLOW_ROUND_ID,
        "granted_table_uuids": ["t-1"],
        "picked": 2,
        "skipped_total": 1,
        "used_gb_hours": 0.04,
        "budget_gb_hours": 0.05,
    }


def test_a_stale_candidate_stays_retryable():
    """A candidate another writer changed propagates as is, so Temporal retries the round on fresh reads."""
    activities = CompactionRoundActivities(schedule=FakeSchedule(StaleCompactionCandidate("changed")))

    with pytest.raises(StaleCompactionCandidate):
        activities.schedule_compaction_round({"round_id": WORKFLOW_ROUND_ID, "now": NOW.isoformat()})


def test_round_input_is_built_from_the_payload_the_round_workflow_sends():
    """The round input reads the workflow's round id and its ISO ``now``, exactly as the workflow sends them."""
    assert ScheduleCompactionRoundUseCaseInput.from_primitives(
        WORKFLOW_SCHEDULE_REQUEST
    ) == ScheduleCompactionRoundUseCaseInput(round_id=WORKFLOW_ROUND_ID, now=NOW)


def test_schedule_ignores_a_payload_key_it_does_not_read():
    """A key a newer workflow adds does not break the round (tolerant reader)."""
    schedule = FakeSchedule()

    CompactionRoundActivities(schedule=schedule).schedule_compaction_round(
        {**WORKFLOW_SCHEDULE_REQUEST, "added_by_a_newer_workflow": 1}
    )

    assert schedule.requests == [ScheduleCompactionRoundUseCaseInput(round_id=WORKFLOW_ROUND_ID, now=NOW)]


@pytest.mark.parametrize(
    "request_",
    [
        {"round_id": WORKFLOW_ROUND_ID},
        {"now": "2026-11-13T12:00:00+00:00"},
        {"round_id": WORKFLOW_ROUND_ID, "now": "not a time"},
    ],
)
def test_schedule_refuses_an_unreadable_payload_without_retry(request_):  # noqa: ANN001
    """A payload missing its round id or ``now``, or with a ``now`` that is no time, fails the activity at once."""
    schedule = FakeSchedule()

    with pytest.raises(ApplicationError) as caught:
        CompactionRoundActivities(schedule=schedule).schedule_compaction_round(request_)

    assert caught.value.non_retryable
    assert caught.value.type == "InvariantViolation"
    assert schedule.requests == []


def _table(uuid: str) -> Table:
    return Table.register(
        TableId(uuid), TableName(catalog="iceberg", namespace="retail", table=uuid), TableDiscoveryRuleId.new(), NOW
    )


def _candidate(table: str, value: str, *, score: float, gb_hours: float) -> CompactionCandidate:
    return CompactionCandidate.create(
        table_uuid=TableId(table),
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"day={value}",
        score=CandidateScore(reducible_files=5, data_bytes=1000, estimated_gb_hours=gb_hours, score=score),
        last_written_at=None,
        hold_reason=None,
        now=NOW - timedelta(minutes=5),
    )


def test_round_activity_returns_the_payload_the_round_workflow_reads():
    """Pin the round's payload as Temporal writes it: the granted tables as a list and the GB·hours as floats.

    The budget is configured as an int, as a deployment may set it; the payload still carries ``1.0``.
    """
    tables = InMemoryTablesRepo()
    for uuid in ("t-1", "t-2"):
        tables.create(_table(uuid))
    candidates = InMemoryCompactionCandidatesRepo()
    candidates.save_all(
        [
            _candidate("t-1", "a", score=0.9, gb_hours=0.5),
            _candidate("t-2", "b", score=0.8, gb_hours=0.5),
            _candidate("t-1", "c", score=0.7, gb_hours=0.5),
        ]
    )
    service = ScheduleCompactionRoundService(
        candidates,
        InMemoryCompactionRoundsRepo(),
        tables,
        weights=PriorityWeights(),
        budget_gb_hours=1,
        partitions_per_run=10,
        sla={priority: timedelta(hours=1) for priority in MaintenancePriority},
        grant_lease=timedelta(minutes=10),
        rounds_kept=500,
    )

    result = CompactionRoundActivities(schedule=service).schedule_compaction_round(dict(WORKFLOW_SCHEDULE_REQUEST))

    assert json.dumps(result) == (
        '{"round_id": "cr-01kaa4zc9qf3v8d2m6xk0w7b2r", "granted_table_uuids": ["t-1", "t-2"], '
        '"picked": 2, "skipped_total": 1, "used_gb_hours": 1.0, "budget_gb_hours": 1.0}'
    )
