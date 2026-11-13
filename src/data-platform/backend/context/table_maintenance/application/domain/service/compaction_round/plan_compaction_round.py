"""Define the plan_compaction_round domain service."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import CandidateState
from context.table_maintenance.application.domain.model.compaction_round import (
    CompactionRound,
    RoundPick,
    RoundSkip,
    SkipReason,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime, timedelta

    from context.table_maintenance.application.domain.model.compaction_candidate import CompactionCandidate
    from context.table_maintenance.application.domain.model.compaction_round import (
        CompactionRoundId,
        PriorityWeights,
    )
    from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority

_TOLERANCE = 1e-9


def plan_compaction_round(  # noqa: PLR0913
    candidates: Sequence[CompactionCandidate],
    *,
    round_id: CompactionRoundId,
    weights: PriorityWeights,
    budget_gb_hours: float,
    partitions_per_run: int,
    sla: Mapping[MaintenancePriority, timedelta],
    now: datetime,
    skipped_kept: int = 20,
) -> CompactionRound:
    """Decide which pending candidates, across every table, one compaction round grants.

    ``candidates`` are the unheld candidates of every table: the pending ones
    are ranked, the others only tell which tables are busy (a live grant or
    run, or a run not observed since it finished); a busy table's pending
    candidates are skipped ``table_busy``. The rest are ranked by score times
    the weight of their priority, ties by the candidate rank (then the table).
    The round walks the ranking in strict order: a table's candidates past
    ``partitions_per_run`` are skipped ``table_share_used`` and the walk goes
    on; otherwise it takes each candidate while the GB·hour budget lasts and
    stops at the first one that does not fit, so everything after it is
    skipped ``budget_used`` even if smaller; the first candidate is always
    taken, so a partition larger than the budget is not starved. The SLA does
    not change the order: it only marks a candidate overdue.
    """
    busy = {c.table_uuid.value for c in candidates if c.keeps_its_table_busy(now)}
    ranked = sorted(
        (c for c in candidates if c.state is CandidateState.PENDING),
        key=lambda c: (-c.score.score * weights.weight(c.priority), *c.rank, c.table_uuid.value),
    )
    picks: list[RoundPick] = []
    skips: list[RoundSkip] = []
    per_table: Counter[str] = Counter()
    used = 0.0
    stopped = False
    for candidate in ranked:
        cost = candidate.score.estimated_gb_hours
        reason: SkipReason | None = None
        if candidate.table_uuid.value in busy:
            reason = SkipReason.TABLE_BUSY
        elif per_table[candidate.table_uuid.value] >= partitions_per_run:
            reason = SkipReason.TABLE_SHARE_USED
        elif stopped:
            reason = SkipReason.BUDGET_USED
        elif picks and used + cost > budget_gb_hours + _TOLERANCE:
            stopped = True
            reason = SkipReason.BUDGET_USED
        if reason is None:
            picks.append(_pick(candidate, weights, sla, now))
            per_table[candidate.table_uuid.value] += 1
            used += cost
        else:
            skips.append(_skip(candidate, weights, sla, now, reason))
    return CompactionRound(
        id=round_id,
        started_at=now,
        budget_gb_hours=budget_gb_hours,
        used_gb_hours=sum(p.estimated_gb_hours for p in picks),
        picks=tuple(picks),
        skips=tuple(skips[: max(0, skipped_kept)]),
        skipped_total=len(skips),
    )


def _pick(
    candidate: CompactionCandidate,
    weights: PriorityWeights,
    sla: Mapping[MaintenancePriority, timedelta],
    now: datetime,
) -> RoundPick:
    return RoundPick(
        table_uuid=candidate.table_uuid,
        partition=candidate.partition,
        label=candidate.label,
        priority=candidate.priority,
        score=candidate.score.score,
        weighted_score=candidate.score.score * weights.weight(candidate.priority),
        estimated_gb_hours=candidate.score.estimated_gb_hours,
        overdue=candidate.overdue(sla, now),
    )


def _skip(
    candidate: CompactionCandidate,
    weights: PriorityWeights,
    sla: Mapping[MaintenancePriority, timedelta],
    now: datetime,
    reason: SkipReason,
) -> RoundSkip:
    return RoundSkip(
        table_uuid=candidate.table_uuid,
        partition=candidate.partition,
        label=candidate.label,
        priority=candidate.priority,
        score=candidate.score.score,
        weighted_score=candidate.score.score * weights.weight(candidate.priority),
        estimated_gb_hours=candidate.score.estimated_gb_hours,
        overdue=candidate.overdue(sla, now),
        reason=reason,
    )
