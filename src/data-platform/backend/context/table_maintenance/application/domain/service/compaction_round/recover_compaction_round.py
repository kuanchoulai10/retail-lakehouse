"""Define the recover_compaction_round domain service."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_round import CompactionRound, RoundPick

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime, timedelta

    from context.table_maintenance.application.domain.model.compaction_candidate import CompactionCandidate
    from context.table_maintenance.application.domain.model.compaction_round import (
        CompactionRoundId,
        PriorityWeights,
    )
    from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority


def recover_compaction_round(  # noqa: PLR0913
    granted: Sequence[CompactionCandidate],
    *,
    round_id: CompactionRoundId,
    weights: PriorityWeights,
    budget_gb_hours: float,
    sla: Mapping[MaintenancePriority, timedelta],
    now: datetime,
) -> CompactionRound:
    """Rebuild the record of a round whose grants were saved but whose record was not.

    ``granted`` are the candidates that name ``round_id`` as their grant
    (still granted, or already claimed by their table). The record lists them
    as the picks, in the order the round ranked them; the skips were not kept,
    so it has none and ``skipped_total`` is 0.
    """
    ranked = sorted(
        granted,
        key=lambda c: (-c.score.score * weights.weight(c.priority), *c.rank, c.table_uuid.value),
    )
    picks = tuple(
        RoundPick(
            table_uuid=c.table_uuid,
            partition=c.partition,
            label=c.label,
            priority=c.priority,
            score=c.score.score,
            weighted_score=c.score.score * weights.weight(c.priority),
            estimated_gb_hours=c.score.estimated_gb_hours,
            overdue=c.overdue(sla, now),
        )
        for c in ranked
    )
    return CompactionRound(
        id=round_id,
        started_at=now,
        budget_gb_hours=budget_gb_hours,
        used_gb_hours=math.fsum(p.estimated_gb_hours for p in picks),
        picks=picks,
        skips=(),
        skipped_total=0,
    )
