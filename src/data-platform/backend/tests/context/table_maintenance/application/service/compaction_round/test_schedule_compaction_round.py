"""Test the ScheduleCompactionRoundService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    PartitionKey,
    StaleCompactionCandidate,
)
from context.table_maintenance.application.domain.model.compaction_round import (
    CompactionRoundId,
    PriorityWeights,
    SkipReason,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.port.inbound.compaction_round import (
    ScheduleCompactionRoundUseCaseInput,
)
from context.table_maintenance.application.service.compaction_round import ScheduleCompactionRoundService
from tests.context.table_maintenance.fakes.in_memory_compaction_candidates_repo import (
    InMemoryCompactionCandidatesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_compaction_rounds_repo import InMemoryCompactionRoundsRepo

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
SLA = {
    MaintenancePriority.P0: timedelta(hours=1),
    MaintenancePriority.P1: timedelta(hours=4),
    MaintenancePriority.P2: timedelta(hours=8),
}
GRANT_LEASE = timedelta(minutes=10)


def _candidate(table: str, value: str, *, score: float, gb_hours: float = 0.02) -> CompactionCandidate:
    return CompactionCandidate.create(
        table_uuid=TableId(table),
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"day={value}",
        score=CandidateScore(reducible_files=5, data_bytes=1000, estimated_gb_hours=gb_hours, score=score),
        last_written_at=None,
        hold_reason=None,
        now=NOW - timedelta(minutes=5),
    )


def _service(candidates, rounds, *, rounds_kept: int = 500):  # noqa: ANN001, ANN202
    return ScheduleCompactionRoundService(
        candidates,
        rounds,
        weights=PriorityWeights(),
        budget_gb_hours=0.05,
        partitions_per_run=10,
        sla=SLA,
        grant_lease=GRANT_LEASE,
        rounds_kept=rounds_kept,
    )


def _run(service, round_id: str = "round-1", now: datetime = NOW):  # noqa: ANN001, ANN202
    return service.execute(ScheduleCompactionRoundUseCaseInput(round_id=round_id, now=now))


def _states(candidates) -> dict[str, CandidateState]:  # noqa: ANN001
    return {str(c.partition.values[0]): c.state for c in candidates.list_all()}


@pytest.fixture
def candidates() -> InMemoryCompactionCandidatesRepo:
    """Provide three pending candidates over two tables; the budget fits the best two."""
    repo = InMemoryCompactionCandidatesRepo()
    repo.save_all(
        [_candidate("t-1", "a", score=0.9), _candidate("t-2", "b", score=0.8), _candidate("t-1", "c", score=0.7)]
    )
    return repo


def test_grants_the_picked_candidates_and_saves_the_round(candidates):  # noqa: ANN001
    """The picks are granted to their tables under a lease, and the round is recorded."""
    rounds = InMemoryCompactionRoundsRepo()

    output = _run(_service(candidates, rounds))

    assert (output.round_id, output.picked, output.skipped_total) == ("round-1", 2, 1)
    assert output.granted_table_uuids == ["t-1", "t-2"]
    assert output.used_gb_hours == pytest.approx(0.04)
    assert output.budget_gb_hours == 0.05
    granted = [c for c in candidates.list_all() if c.state is CandidateState.GRANTED]
    assert sorted(str(c.partition.values[0]) for c in granted) == ["a", "b"]
    assert {(c.granted_round_id, c.lease_expires_at) for c in granted} == {("round-1", NOW + GRANT_LEASE)}
    stored = rounds.get(CompactionRoundId("round-1"))
    assert stored is not None
    assert [p.label for p in stored.picks] == ["day=a", "day=b"]
    assert [(s.label, s.reason) for s in stored.skips] == [("day=c", SkipReason.BUDGET_USED)]


def test_leaves_skipped_candidates_pending(candidates):  # noqa: ANN001
    """A candidate the round skipped stays pending, still counting its wait."""
    _run(_service(candidates, InMemoryCompactionRoundsRepo()))

    (left,) = [c for c in candidates.list_all() if c.partition.values == ("c",)]
    assert left.state is CandidateState.PENDING
    assert left.pending_since == NOW - timedelta(minutes=5)


def test_a_round_with_no_pending_candidate_is_recorded_empty():
    """With nothing pending the round is still recorded, picking nothing and naming no table."""
    rounds = InMemoryCompactionRoundsRepo()

    output = _run(_service(InMemoryCompactionCandidatesRepo(), rounds))

    assert (output.picked, output.granted_table_uuids, output.used_gb_hours) == (0, [], 0.0)
    assert rounds.get(CompactionRoundId("round-1")) is not None


def test_a_stale_candidate_saves_neither_grants_nor_round(candidates):  # noqa: ANN001
    """When a plan saved a candidate after the round read it, the round raises and stores nothing."""
    rounds = InMemoryCompactionRoundsRepo()
    read = candidates.list_pending

    def read_then_a_plan_saves():  # noqa: ANN202
        pending = read()
        (b,) = [c for c in candidates.list_all() if c.partition.values == ("b",)]
        b.observe(b.score, None, None, NOW)
        candidates.save_all([b])
        return pending

    candidates.list_pending = read_then_a_plan_saves

    with pytest.raises(StaleCompactionCandidate):
        _run(_service(candidates, rounds))

    assert set(_states(candidates).values()) == {CandidateState.PENDING}
    assert rounds.list_all() == []


def test_a_retried_round_returns_what_it_recorded(candidates):  # noqa: ANN001
    """A round run again under the same id (an activity retry after it saved) grants nothing more."""
    rounds = InMemoryCompactionRoundsRepo()
    service = _service(candidates, rounds)
    first = _run(service)
    candidates.save_all([_candidate("t-3", "d", score=0.99)])

    again = _run(service, now=NOW + timedelta(seconds=5))

    assert again == first
    assert _states(candidates)["d"] is CandidateState.PENDING


def test_purges_old_rounds(candidates):  # noqa: ANN001
    """Only the newest rounds are kept."""
    rounds = InMemoryCompactionRoundsRepo()
    service = _service(candidates, rounds, rounds_kept=2)

    for i in range(4):
        _run(service, round_id=f"round-{i}", now=NOW + timedelta(minutes=i))

    assert sorted(r.id.value for r in rounds.list_all()) == ["round-2", "round-3"]
