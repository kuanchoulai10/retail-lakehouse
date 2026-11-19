"""Tests for the recover_compaction_round domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CompactionCandidate,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.compaction_round import CompactionRoundId, PriorityWeights
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.domain.service.compaction_round import recover_compaction_round

ROUND_1 = "cr-00000000000000000000000001"

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
ROUND = CompactionRoundId(ROUND_1)
SLA = {
    MaintenancePriority.P0: timedelta(hours=1),
    MaintenancePriority.P1: timedelta(hours=4),
    MaintenancePriority.P2: timedelta(hours=8),
}


def _granted(table: str, value: str, score: float, priority: MaintenancePriority) -> CompactionCandidate:
    candidate = CompactionCandidate.create(
        table_uuid=TableId(table),
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"day={value}",
        score=CandidateScore(reducible_files=5, data_bytes=1000, estimated_gb_hours=0.02, score=score),
        last_written_at=None,
        hold_reason=None,
        now=NOW - timedelta(hours=2),
        priority=priority,
    )
    candidate.grant(ROUND.value, NOW + timedelta(minutes=10), NOW)
    return candidate


def test_lists_the_grants_as_picks_in_rank_order_without_skips():
    """The rebuilt record ranks by weighted score, costs the picks and keeps no skips."""
    round_ = recover_compaction_round(
        [_granted("t-2", "low", 0.9, MaintenancePriority.P2), _granted("t-1", "hot", 0.5, MaintenancePriority.P0)],
        round_id=ROUND,
        weights=PriorityWeights(),
        budget_gb_hours=0.05,
        sla=SLA,
        now=NOW,
    )

    assert [p.label for p in round_.picks] == ["day=hot", "day=low"]
    assert [p.overdue for p in round_.picks] == [True, False]
    assert round_.used_gb_hours == pytest.approx(0.04)
    assert (round_.skips, round_.skipped_total, round_.started_at) == ((), 0, NOW)
