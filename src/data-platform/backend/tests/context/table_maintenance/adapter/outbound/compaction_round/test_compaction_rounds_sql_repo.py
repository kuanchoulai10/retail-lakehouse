"""Test the repositories of the CompactionRound aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.compaction_round.sql import CompactionRoundsSqlRepo
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
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.compaction_round import CompactionRoundsRepo

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
    )


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> CompactionRoundsRepo:
    """Provide each repository implementation."""
    if request.param == "sql":
        return CompactionRoundsSqlRepo(engine)
    return InMemoryCompactionRoundsRepo()


def test_round_trip_keeps_picks_and_skips(repo: CompactionRoundsRepo):
    """A round with picks and skips loads back equal, field by field."""
    saved = _round("r-1")
    repo.save(saved)

    loaded = repo.get(CompactionRoundId("r-1"))
    assert loaded is not None
    assert loaded.model_dump() == saved.model_dump()


def test_save_again_replaces_the_round(repo: CompactionRoundsRepo):
    """Saving a round under an id already stored replaces it, so a retried round stays one row."""
    repo.save(_round("r-1"))
    repo.save(_round("r-1", NOW + timedelta(seconds=1)))

    (only,) = repo.list_all()
    assert only.started_at == NOW + timedelta(seconds=1)


def test_unknown_round_is_none(repo: CompactionRoundsRepo):
    """An id never stored reads as None."""
    assert repo.get(CompactionRoundId("nope")) is None


def test_list_recent_is_newest_first_and_pages_by_start(repo: CompactionRoundsRepo):
    """Rounds list newest first, at most ``limit``, strictly before ``before``."""
    for i in range(5):
        repo.save(_round(f"r-{i}", NOW + timedelta(minutes=i)))

    assert [r.id.value for r in repo.list_recent(limit=2)] == ["r-4", "r-3"]
    assert [r.id.value for r in repo.list_recent(limit=2, before=NOW + timedelta(minutes=3))] == ["r-2", "r-1"]


def test_purge_keeps_the_newest(repo: CompactionRoundsRepo):
    """Purging keeps the ``keep`` newest rounds and says how many went."""
    for i in range(5):
        repo.save(_round(f"r-{i}", NOW + timedelta(minutes=i)))

    assert repo.purge(keep=2) == 3
    assert sorted(r.id.value for r in repo.list_all()) == ["r-3", "r-4"]
    assert repo.purge(keep=2) == 0
