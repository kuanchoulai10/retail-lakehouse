"""Test the repositories of the CompactionCandidate aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, insert, text

from context.table_maintenance.adapter.outbound.compaction_candidate.sql import (
    CompactionCandidatesSqlRepo,
    compaction_candidates_table,
)
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    CompactionCandidateId,
    HoldReason,
    PartitionKey,
    StaleCompactionCandidate,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from tests.context.table_maintenance.fakes.in_memory_compaction_candidates_repo import (
    InMemoryCompactionCandidatesRepo,
)

if TYPE_CHECKING:
    from pathlib import Path

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
    candidate.grant("round-1", NOW + timedelta(minutes=10), NOW)
    candidate.claim(RUN, NOW + timedelta(hours=19), NOW)
    candidate.observe(
        SCORE, NOW - timedelta(minutes=2), None, NOW + timedelta(minutes=1), priority=MaintenancePriority.P0
    )

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
    """Saving a candidate read from the store replaces its row."""
    repo.save_all([_candidate()])
    again = repo.list_by_table(TABLE)[0]
    again.observe(CandidateScore(reducible_files=9, data_bytes=10, estimated_gb_hours=0.0, score=0.9), None, None, NOW)
    repo.save_all([again])

    stored = repo.list_by_table(TABLE)
    assert len(stored) == 1
    assert stored[0].score.reducible_files == 9


def test_round_trip_of_a_granted_candidate(repo: CompactionCandidatesRepo):
    """A granted candidate keeps its round, lease, pending start and priority."""
    candidate = _candidate()
    candidate.observe(SCORE, None, None, NOW, priority=MaintenancePriority.P1)
    candidate.grant("round-7", NOW + timedelta(minutes=10), NOW + timedelta(minutes=1))
    repo.save_all([candidate])

    loaded = repo.get(candidate.id)
    assert loaded is not None
    assert loaded.model_dump() == candidate.model_dump()
    assert (loaded.state, loaded.granted_round_id, loaded.priority) == (
        CandidateState.GRANTED,
        "round-7",
        MaintenancePriority.P1,
    )
    assert loaded.pending_since == NOW


def test_save_increments_the_version(repo: CompactionCandidatesRepo):
    """The first save stores version 1 and every later save one more; the saved candidate takes it."""
    candidate = _candidate()
    assert candidate.version == 0
    repo.save_all([candidate])
    assert candidate.version == 1
    loaded = repo.get(candidate.id)
    assert loaded is not None
    assert loaded.version == 1
    loaded.observe(SCORE, None, None, NOW + timedelta(minutes=1))
    repo.save_all([loaded])
    assert loaded.version == 2
    again = repo.get(candidate.id)
    assert again is not None
    assert again.version == 2


def test_save_of_a_new_candidate_for_a_stored_partition_is_stale(repo: CompactionCandidatesRepo):
    """Two writers that both create the same partition's candidate: the second one is refused."""
    repo.save_all([_candidate()])
    with pytest.raises(StaleCompactionCandidate):
        repo.save_all([_candidate()])


def test_list_pending_reads_every_table(repo: CompactionCandidatesRepo):
    """Pending candidates of every table are listed; held, granted and claimed ones are not."""
    held = _candidate(("held",), hold=HoldReason.NOT_DUE)
    granted = _candidate(("granted",))
    granted.grant("round-1", NOW + timedelta(minutes=10), NOW)
    claimed = _candidate(("claimed",))
    claimed.grant("round-1", NOW + timedelta(minutes=10), NOW)
    claimed.claim(RUN, NOW + timedelta(hours=1), NOW)
    mine, theirs = _candidate(("eu",)), _candidate(("eu",), table=TableId("t-2"))
    repo.save_all([held, granted, claimed, mine, theirs])

    assert sorted(c.id.value for c in repo.list_pending()) == sorted([mine.id.value, theirs.id.value])


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
    for candidate, run in ((claimed, RUN), (other, TableMaintenanceRunId("run-2"))):
        candidate.grant("round-1", NOW + timedelta(minutes=10), NOW)
        candidate.claim(run, NOW + timedelta(hours=1), NOW)
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


@pytest.fixture
def file_engine(tmp_path: Path) -> Engine:
    """Provide a SQLite database in a file, so two repositories share it like two workers."""
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    create_schema(engine)
    return engine


def test_save_of_a_stale_candidate_raises_and_saves_nothing(file_engine: Engine):
    """Two writers load the same candidates; after one saves, the other's whole save is refused."""
    first, second = CompactionCandidatesSqlRepo(file_engine), CompactionCandidatesSqlRepo(file_engine)
    first.save_all([_candidate(("eu",)), _candidate(("us",))])
    a1, _ = first.list_by_table(TABLE)
    b1, b2 = second.list_by_table(TABLE)
    a1.grant("round-1", NOW + timedelta(minutes=10), NOW)
    first.save_all([a1])

    b2.observe(CandidateScore(reducible_files=1, data_bytes=1, estimated_gb_hours=0.0, score=0.1), None, None, NOW)
    b1.observe(CandidateScore(reducible_files=1, data_bytes=1, estimated_gb_hours=0.0, score=0.1), None, None, NOW)
    with pytest.raises(StaleCompactionCandidate):
        second.save_all([b2, b1])

    stored = {c.partition.values: c for c in first.list_by_table(TABLE)}
    assert stored[("eu",)].state is CandidateState.GRANTED
    assert stored[("us",)].score == SCORE
    assert stored[("us",)].version == 1
    assert (b1.version, b2.version) == (1, 1)


def test_reads_rows_written_before_the_new_columns(file_engine: Engine):
    """A row stored before versions, priorities, grants and pending starts reads as version 1, P2, no grant."""
    candidate = _candidate()
    with file_engine.begin() as connection:
        for column in ("version", "priority", "granted_round_id", "pending_since"):
            connection.execute(text(f"ALTER TABLE compaction_candidates DROP COLUMN {column}"))
    create_schema(file_engine)
    values = {
        "id": candidate.id.value,
        "table_uuid": TABLE.value,
        "partition_key": candidate.partition.canonical(),
        "spec_id": 0,
        "label": "region=eu",
        "state": "pending",
        "reducible_files": 7,
        "data_bytes": 10,
        "estimated_gb_hours": 0.1,
        "score": 0.4,
        "observed_at": NOW,
        "updated_at": NOW,
    }
    with file_engine.begin() as connection:
        connection.execute(insert(compaction_candidates_table).values(**values))

    loaded = CompactionCandidatesSqlRepo(file_engine).get(candidate.id)
    assert loaded is not None
    assert (loaded.version, loaded.priority, loaded.granted_round_id, loaded.pending_since) == (
        1,
        MaintenancePriority.P2,
        None,
        None,
    )
