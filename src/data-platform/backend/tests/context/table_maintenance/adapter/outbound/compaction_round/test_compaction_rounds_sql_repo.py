"""Test the repositories of the CompactionRound aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, insert, text

from context.table_maintenance.adapter.outbound.compaction_round.sql import (
    CompactionRoundsSqlRepo,
    compaction_rounds_table,
)
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.domain.model.compaction_candidate import PartitionKey
from context.table_maintenance.application.domain.model.compaction_round import (
    CompactionRound,
    CompactionRoundId,
    RoundPick,
    RoundSkip,
    SkipReason,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from tests.context.table_maintenance.fakes.in_memory_compaction_rounds_repo import InMemoryCompactionRoundsRepo

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.compaction_round import CompactionRoundsRepo
from tests.context.table_maintenance.numbered_id import numbered_id

ROUND_1 = "cr-00000000000000000000000001"
ROUND_2 = "cr-00000000000000000000000002"
ROUND_3 = "cr-00000000000000000000000003"
ROUND_4 = "cr-00000000000000000000000004"

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)


def _round(round_id: str, started_at: datetime = NOW) -> CompactionRound:
    pick = RoundPick(
        table_uuid=TableId("t-1"),
        partition=PartitionKey(spec_id=0, values=(19000, "o'neil", None, 1.5, True)),
        label="day=2022-01-08, region=o'neil",
        priority=MaintenancePriority.P0,
        score=0.3,
        weighted_score=1.2,
        estimated_gb_hours=0.2,
        overdue=True,
    )
    skip = RoundSkip(
        table_uuid=TableId("t-2"),
        partition=PartitionKey.whole_table(),
        label="whole table",
        priority=MaintenancePriority.P2,
        score=0.9,
        weighted_score=0.9,
        estimated_gb_hours=0.01,
        overdue=False,
        reason=SkipReason.BUDGET_USED,
    )
    return CompactionRound(
        id=CompactionRoundId(round_id),
        started_at=started_at,
        budget_gb_hours=0.05,
        used_gb_hours=0.2,
        picks=(pick,),
        skips=(skip,),
        skipped_total=7,
        busy_skipped=5,
    )


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> CompactionRoundsRepo:
    """Provide each repository implementation."""
    if request.param == "sql":
        return CompactionRoundsSqlRepo(engine)
    return InMemoryCompactionRoundsRepo()


def test_round_trip_keeps_picks_and_skips(repo: CompactionRoundsRepo):
    """A round with picks and skips loads back equal, field by field."""
    saved = _round(ROUND_1)
    repo.save(saved)

    loaded = repo.get(CompactionRoundId(ROUND_1))
    assert loaded is not None
    assert loaded.model_dump() == saved.model_dump()


def test_save_again_replaces_the_round(repo: CompactionRoundsRepo):
    """Saving a round under an id already stored replaces it, so a retried round stays one row."""
    repo.save(_round(ROUND_1))
    repo.save(_round(ROUND_1, NOW + timedelta(seconds=1)))

    (only,) = repo.list_all()
    assert only.started_at == NOW + timedelta(seconds=1)


def test_unknown_round_is_none(repo: CompactionRoundsRepo):
    """An id never stored reads as None."""
    assert repo.get(CompactionRoundId.new()) is None


def test_list_recent_is_newest_first_and_pages_by_start(repo: CompactionRoundsRepo):
    """Rounds list newest first, at most ``limit``, strictly before ``before``."""
    for i in range(5):
        repo.save(_round(numbered_id("cr", i), NOW + timedelta(minutes=i)))

    assert [r.id.value for r in repo.list_recent(limit=2)] == [ROUND_4, ROUND_3]
    assert [r.id.value for r in repo.list_recent(limit=2, before=NOW + timedelta(minutes=3))] == [ROUND_2, ROUND_1]


def test_purge_keeps_the_newest(repo: CompactionRoundsRepo):
    """Purging keeps the ``keep`` newest rounds and says how many went."""
    for i in range(5):
        repo.save(_round(numbered_id("cr", i), NOW + timedelta(minutes=i)))

    assert repo.purge(keep=2) == 3
    assert sorted(r.id.value for r in repo.list_all()) == [ROUND_3, ROUND_4]
    assert repo.purge(keep=2) == 0


def test_reads_a_round_recorded_before_busy_tables_were_counted_apart(tmp_path: Path):
    """A round stored without a busy count reads as none; its busy skips, if any, are among its skips."""
    engine = create_engine(f"sqlite:///{tmp_path / 'rounds.db'}")
    create_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE compaction_rounds DROP COLUMN busy_skipped"))
    create_schema(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(compaction_rounds_table).values(
                id=ROUND_1,
                started_at=NOW,
                budget_gb_hours=0.05,
                used_gb_hours=0.0,
                picks_json=[],
                skips_json=[],
                skipped_total=0,
            )
        )

    loaded = CompactionRoundsSqlRepo(engine).get(CompactionRoundId(ROUND_1))

    assert loaded is not None
    assert loaded.busy_skipped == 0
