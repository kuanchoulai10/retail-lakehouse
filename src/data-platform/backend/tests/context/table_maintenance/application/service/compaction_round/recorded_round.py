"""Define the recorded_round helper the round read tests store."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from datetime import datetime


def recorded_round(round_id: str, started_at: datetime) -> CompactionRound:
    """Return a round that granted one P0 partition of ``t-1`` and skipped one whole-table P2 candidate of ``t-2``."""
    return CompactionRound(
        id=CompactionRoundId(round_id),
        started_at=started_at,
        budget_gb_hours=0.05,
        used_gb_hours=0.04,
        picks=(
            RoundPick(
                table_uuid=TableId("t-1"),
                partition=PartitionKey(spec_id=0, values=("2026-11-01",)),
                label="day=2026-11-01",
                priority=MaintenancePriority.P0,
                score=0.5,
                weighted_score=2.0,
                estimated_gb_hours=0.04,
                overdue=True,
            ),
        ),
        skips=(
            RoundSkip(
                table_uuid=TableId("t-2"),
                partition=PartitionKey.whole_table(),
                label="whole table",
                priority=MaintenancePriority.P2,
                score=0.6,
                weighted_score=0.6,
                estimated_gb_hours=0.03,
                overdue=False,
                reason=SkipReason.BUDGET_USED,
            ),
        ),
        skipped_total=3,
    )
