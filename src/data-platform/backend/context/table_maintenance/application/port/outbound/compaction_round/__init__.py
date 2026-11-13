"""Outbound ports for the compaction_round group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.compaction_candidate import PartitionKey
from context.table_maintenance.application.domain.model.compaction_round import (
    CompactionRound,
    CompactionRoundId,
    RoundPick,
    RoundSkip,
)
from context.table_maintenance.application.port.outbound.compaction_round.compaction_rounds_repo import (
    CompactionRoundsRepo,
)

__all__ = [
    "CompactionRound",
    "CompactionRoundId",
    "CompactionRoundsRepo",
    "PartitionKey",
    "RoundPick",
    "RoundSkip",
]
