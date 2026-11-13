"""Test the repositories of the CompactionCandidate aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.compaction_candidate.sql import (
    CompactionCandidatesSqlRepo,
)
from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    CompactionCandidateId,
    HoldReason,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from tests.context.table_maintenance.fakes.in_memory_compaction_candidates_repo import (
    InMemoryCompactionCandidatesRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.compaction_candidate import (
        CompactionCandidatesRepo,
    )

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
TABLE = TableId("t-1")
RUN = TableMaintenanceRunId("run-1")
SCORE = CandidateScore(reducible_files=7, data_bytes=3 * 1024**3, estimated_gb_hours=0.375, score=0.4125)


def _candidate(
    values: tuple[str | int | float | bool | None, ...] = ("eu",),
    *,
    spec_id: int = 0,
    table: TableId = TABLE,
    hold: HoldReason | None = None,
    score: CandidateScore = SCORE,
) -> CompactionCandidate:
    return CompactionCandidate.create(
        table_uuid=table,
        partition=PartitionKey(spec_id=spec_id, values=values),
        label="region=eu",
        score=score,
        last_written_at=None,
        hold_reason=hold,
        now=NOW,
    )


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> CompactionCandidatesRepo:
    """Provide each repository implementation."""
    if request.param == "sql":
        return CompactionCandidatesSqlRepo(engine)
    return InMemoryCompactionCandidatesRepo()


def test_round_trip_keeps_every_field(repo: CompactionCandidatesRepo):
    """A claimed candidate with every optional field set loads back equal."""
    candidate = _candidate((19000, "o'neil", None, 1.5, True))
    candidate.observe(
        SCORE,
        NOW - timedelta(minutes=3),
        None,
        NOW,
        waiting_since=NOW - timedelta(minutes=10),
        label="day=2022-01-08, region=o'neil",
    )
    candidate.claim(RUN, NOW + timedelta(hours=19), NOW)
    candidate.observe(SCORE, NOW - timedelta(minutes=2), None, NOW + timedelta(minutes=1))

    repo.save_all([candidate])

    assert repo.get(candidate.id) == candidate
    loaded = repo.get(candidate.id)
    assert loaded is not None
    assert loaded.model_dump() == candidate.model_dump()


def test_round_trip_keeps_the_nones(repo: CompactionCandidatesRepo):
    """A held whole-table candidate without a last write, wait, claim or lease loads back equal."""
    candidate = CompactionCandidate.create(
        table_uuid=TABLE,
        partition=PartitionKey.whole_table(),
        label="whole table",
        score=SCORE,
        last_written_at=None,
        hold_reason=HoldReason.TOO_SMALL,
        now=NOW,
    )

    repo.save_all([candidate])

    loaded = repo.get(candidate.id)
    assert loaded is not None
    assert loaded.model_dump() == candidate.model_dump()
    assert loaded.state is CandidateState.HELD


def test_save_all_keeps_one_row_per_table_and_partition(repo: CompactionCandidatesRepo):
    """Saving the same partition again replaces its row."""
    first = _candidate()
    repo.save_all([first])
    again = _candidate(score=CandidateScore(reducible_files=9, data_bytes=10, estimated_gb_hours=0.0, score=0.9))
    repo.save_all([again])

    stored = repo.list_by_table(TABLE)
    assert len(stored) == 1
    assert stored[0].score.reducible_files == 9


def test_two_spec_ids_with_equal_values_are_two_rows(repo: CompactionCandidatesRepo):
    """Partition evolution: the same values under two specs are two candidates."""
    repo.save_all([_candidate(spec_id=0), _candidate(spec_id=1)])

    assert sorted(c.partition.spec_id for c in repo.list_by_table(TABLE)) == [0, 1]


def test_list_by_table_returns_only_that_table(repo: CompactionCandidatesRepo):
    """Candidates of another table are not listed."""
    repo.save_all([_candidate(("eu",)), _candidate(("us",)), _candidate(("eu",), table=TableId("t-2"))])

    assert sorted(c.partition.values for c in repo.list_by_table(TABLE)) == [("eu",), ("us",)]


def test_list_by_run_returns_the_candidates_the_run_holds(repo: CompactionCandidatesRepo):
    """Only the candidates claimed by the run are listed for it."""
    claimed, other, free = _candidate(("eu",)), _candidate(("us",)), _candidate(("ap",))
    claimed.claim(RUN, NOW + timedelta(hours=1), NOW)
    other.claim(TableMaintenanceRunId("run-2"), NOW + timedelta(hours=1), NOW)
    repo.save_all([claimed, other, free])

    assert [c.id for c in repo.list_by_run(RUN)] == [claimed.id]


def test_delete_removes_only_the_named_candidates(repo: CompactionCandidatesRepo):
    """Deleting by id leaves the others; an unknown id is ignored."""
    eu, us = _candidate(("eu",)), _candidate(("us",))
    repo.save_all([eu, us])

    repo.delete([eu.id, CompactionCandidateId("nope")])

    assert [c.id for c in repo.list_by_table(TABLE)] == [us.id]


def test_delete_by_table_removes_every_candidate_of_the_table(repo: CompactionCandidatesRepo):
    """Deleting by table leaves other tables' candidates."""
    kept = _candidate(table=TableId("t-2"))
    repo.save_all([_candidate(("eu",)), _candidate(("us",)), kept])

    repo.delete_by_table(TABLE)

    assert repo.list_by_table(TABLE) == []
    assert [c.id for c in repo.list_all()] == [kept.id]


def test_create_inserts_a_new_candidate(repo: CompactionCandidatesRepo):
    """The generic create stores a candidate like save_all."""
    candidate = _candidate()
    assert repo.create(candidate) == candidate
    assert repo.get(candidate.id) == candidate
