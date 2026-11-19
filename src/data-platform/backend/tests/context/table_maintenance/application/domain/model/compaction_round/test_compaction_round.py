"""Tests for the CompactionRound aggregate and its value objects."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.compaction_candidate import PartitionKey
from context.table_maintenance.application.domain.model.compaction_round import (
    CompactionRound,
    CompactionRoundId,
    PriorityWeights,
    RoundPick,
    RoundSkip,
    SkipReason,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority

ROUND_1 = "cr-00000000000000000000000001"

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)


def _pick(table: str = "t-1", gb_hours: float = 0.02) -> RoundPick:
    return RoundPick(
        table_uuid=TableId(table),
        partition=PartitionKey(spec_id=0, values=("a",)),
        label="day=a",
        priority=MaintenancePriority.P1,
        score=0.5,
        weighted_score=1.0,
        estimated_gb_hours=gb_hours,
        overdue=False,
    )


def _skip() -> RoundSkip:
    return RoundSkip(
        table_uuid=TableId("t-2"),
        partition=PartitionKey(spec_id=0, values=("b",)),
        label="day=b",
        priority=MaintenancePriority.P2,
        score=0.4,
        weighted_score=0.4,
        estimated_gb_hours=0.02,
        overdue=True,
        reason=SkipReason.BUDGET_USED,
    )


def test_weights_give_each_priority_its_weight():
    """The weight of a priority is the one configured for it."""
    weights = PriorityWeights(p0=4.0, p1=2.0, p2=1.0)
    assert [weights.weight(p) for p in MaintenancePriority] == [4.0, 2.0, 1.0]


@pytest.mark.parametrize("weights", [{"p0": 0.0}, {"p1": -1.0}])
def test_weights_must_be_positive(weights):
    """A zero or negative weight would make a priority never ranked."""
    with pytest.raises(InvariantViolation):
        PriorityWeights(**weights)


def test_round_holds_its_picks_and_skips():
    """A round says what it picked, what it skipped and how much of its budget it used."""
    round_ = CompactionRound(
        id=CompactionRoundId(ROUND_1),
        started_at=NOW,
        budget_gb_hours=0.05,
        used_gb_hours=0.02,
        picks=(_pick(),),
        skips=(_skip(),),
        skipped_total=3,
    )
    assert round_.granted_tables() == (TableId("t-1"),)


def test_round_counts_at_least_the_skips_it_keeps():
    """The skipped total cannot be below the number of skips kept."""
    with pytest.raises(InvariantViolation):
        CompactionRound(
            id=CompactionRoundId(ROUND_1),
            started_at=NOW,
            budget_gb_hours=0.05,
            used_gb_hours=0.0,
            picks=(),
            skips=(_skip(),),
            skipped_total=0,
        )


def test_round_used_is_the_sum_of_its_picks():
    """The budget used is what the picks are estimated to cost."""
    with pytest.raises(InvariantViolation):
        CompactionRound(
            id=CompactionRoundId(ROUND_1),
            started_at=NOW,
            budget_gb_hours=0.05,
            used_gb_hours=0.5,
            picks=(_pick(gb_hours=0.02),),
            skips=(),
            skipped_total=0,
        )


def test_round_round_trips_through_primitives():
    """Picks and skips are stored as primitives and read back equal."""
    round_ = CompactionRound(
        id=CompactionRoundId(ROUND_1),
        started_at=NOW,
        budget_gb_hours=0.05,
        used_gb_hours=0.02,
        picks=(_pick(),),
        skips=(_skip(),),
        skipped_total=1,
    )
    assert RoundPick.from_primitives(round_.picks[0].to_primitives()) == round_.picks[0]
    assert RoundSkip.from_primitives(round_.skips[0].to_primitives()) == round_.skips[0]


def test_round_counts_partitions_of_busy_tables_apart_from_its_skips():
    """Partitions of tables busy with compaction are counted, never kept as skips; none by default."""
    round_ = CompactionRound(
        id=CompactionRoundId(ROUND_1),
        started_at=NOW,
        budget_gb_hours=0.05,
        used_gb_hours=0.0,
        picks=(),
        skips=(),
        skipped_total=0,
        busy_skipped=4,
    )
    assert round_.busy_skipped == 4
    assert round_.model_copy(update={"busy_skipped": 0}) == CompactionRound(
        id=CompactionRoundId(ROUND_1),
        started_at=NOW,
        budget_gb_hours=0.05,
        used_gb_hours=0.0,
        picks=(),
        skips=(),
        skipped_total=0,
    )
    with pytest.raises(InvariantViolation):
        round_.model_validate({**round_.model_dump(), "busy_skipped": -1})
