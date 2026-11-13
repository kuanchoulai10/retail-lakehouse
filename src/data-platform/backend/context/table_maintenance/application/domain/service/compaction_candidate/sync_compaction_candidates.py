"""Define the sync_compaction_candidates domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateState,
    CandidateSync,
    CompactionCandidate,
    HoldReason,
)
from context.table_maintenance.application.domain.service.compaction_candidate.score_candidate import (
    score_candidate,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.compaction_candidate import (
        CandidateFilters,
        CandidateScoring,
        ObservedPartition,
    )
    from context.table_maintenance.application.domain.model.table import TableId
    from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority


def sync_compaction_candidates(  # noqa: PLR0913
    table_uuid: TableId,
    existing: Sequence[CompactionCandidate],
    observed: Sequence[ObservedPartition],
    *,
    scoring: CandidateScoring,
    filters: CandidateFilters,
    memory_gb: float,
    throughput_bytes_per_hour: float,
    now: datetime,
    due: bool = True,
    cooling_down: bool = False,
    priority: MaintenancePriority | None = None,
) -> CandidateSync:
    """Bring a table's candidates in line with one observation; the table decides, not a run's report.

    ``observed`` are the partitions that meet the policy's compaction conditions
    now. A new one becomes a candidate; an existing one takes the observation
    (a finished one is pending again, a claim under a live lease is kept); an
    existing candidate not observed is healthy and is removed. A partition with
    less data than the minimum is held as too small; one written within the
    quiet period is held as recently written, until its writes pause or it has
    waited the longest wait in a row. When compaction is not ``due`` every other
    one is held, so no compaction round spends budget on it: in ``cooldown``
    when compaction is ``cooling_down`` (the wait for a round goes on), not due
    otherwise (the wait ends). Every
    candidate takes ``priority``, the applicable policy's (None keeps what each
    has, P2 for a new one).
    """
    by_key = {c.partition.canonical(): c for c in existing}
    saved: list[CompactionCandidate] = []
    seen: set[str] = set()
    next_check_at: datetime | None = None
    for partition in observed:
        key = partition.partition.canonical()
        seen.add(key)
        previous = by_key.get(key)
        score = score_candidate(
            reducible_files=partition.reducible_files,
            data_bytes=partition.data_bytes,
            memory_gb=memory_gb,
            throughput_bytes_per_hour=throughput_bytes_per_hour,
            scoring=scoring,
        )
        recent = partition.last_written_at is not None and now - partition.last_written_at < filters.quiet_period
        waiting_since = None
        if recent:
            waiting_since = previous.waiting_since if previous and previous.waiting_since else now
        hold = _hold_reason(partition, filters, waiting_since, now, due=due, cooling_down=cooling_down)
        if previous is None:
            candidate = CompactionCandidate.create(
                table_uuid=table_uuid,
                partition=partition.partition,
                label=partition.label,
                score=score,
                last_written_at=partition.last_written_at,
                hold_reason=hold,
                now=now,
                waiting_since=waiting_since,
                **({} if priority is None else {"priority": priority}),
            )
        else:
            candidate = previous
            candidate.observe(
                score,
                partition.last_written_at,
                hold,
                now,
                waiting_since=waiting_since,
                label=partition.label,
                priority=priority,
            )
        saved.append(candidate)
        hold_ends = _recent_hold_ends(candidate, partition, filters)
        if hold_ends is not None and (next_check_at is None or hold_ends < next_check_at):
            next_check_at = hold_ends
    removed = tuple(c.id for key, c in by_key.items() if key not in seen)
    return CandidateSync(saved=tuple(saved), removed=removed, next_check_at=next_check_at)


def _hold_reason(
    partition: ObservedPartition,
    filters: CandidateFilters,
    waiting_since: datetime | None,
    now: datetime,
    *,
    due: bool,
    cooling_down: bool,
) -> HoldReason | None:
    if partition.data_bytes < filters.min_partition_bytes:
        return HoldReason.TOO_SMALL
    if waiting_since is not None and now - waiting_since < filters.max_quiet_wait:
        return HoldReason.RECENTLY_WRITTEN
    if not due:
        return HoldReason.COOLDOWN if cooling_down else HoldReason.NOT_DUE
    return None


def _recent_hold_ends(
    candidate: CompactionCandidate, partition: ObservedPartition, filters: CandidateFilters
) -> datetime | None:
    """Return when a recently-written hold ends: the quiet period passes or the longest wait is reached."""
    if candidate.state is not CandidateState.HELD or candidate.hold_reason is not HoldReason.RECENTLY_WRITTEN:
        return None
    if partition.last_written_at is None or candidate.waiting_since is None:
        return None
    return min(partition.last_written_at + filters.quiet_period, candidate.waiting_since + filters.max_quiet_wait)
