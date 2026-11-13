"""Define the pick_compaction_candidates domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidatePick,
    CandidateShortfall,
)
from context.table_maintenance.application.domain.service.compaction_candidate.select_top_candidates import (
    select_top_candidates,
)
from context.table_maintenance.application.domain.service.compaction_candidate.sync_compaction_candidates import (
    sync_compaction_candidates,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.compaction_candidate import (
        CandidateSelection,
        CompactionCandidate,
        ObservedPartition,
    )
    from context.table_maintenance.application.domain.model.table import TableId
    from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId


def pick_compaction_candidates(  # noqa: PLR0913
    table_uuid: TableId,
    existing: Sequence[CompactionCandidate],
    observed: Sequence[ObservedPartition],
    *,
    selection: CandidateSelection,
    memory_gb: float,
    throughput_bytes_per_hour: float,
    released_runs: frozenset[TableMaintenanceRunId],
    pick: bool,
    claim_for: TableMaintenanceRunId | None,
    lease_until: datetime,
    now: datetime,
) -> CandidatePick:
    """Sync a table's candidates with one observation and, when compaction is due, pick the run's share.

    Claims still held by a run in ``released_runs`` (one that has finished, or
    one that never started) are handed back first, so they do not wait out their
    lease. With ``pick``, a run that already holds claims (a retried plan)
    gets those again; otherwise the ``partitions_per_run`` best pending
    candidates are picked and, when ``claim_for`` names the run, claimed for it
    until ``lease_until``. Without any, the shortfall says whether other runs
    hold candidates (and when the first lease ends) or filters hold them all
    (and when the first recently-written hold ends).
    """
    current = [_released(c, released_runs, now) for c in existing]
    sync = sync_compaction_candidates(
        table_uuid,
        current,
        observed,
        scoring=selection.scoring,
        filters=selection.filters,
        memory_gb=memory_gb,
        throughput_bytes_per_hour=throughput_bytes_per_hour,
        now=now,
    )
    if not pick:
        return CandidatePick(saved=sync.saved, removed=sync.removed)
    own = [
        c for c in sync.saved if c.state.holds_a_claim and claim_for is not None and c.claimed_by_run_id == claim_for
    ]
    selected = tuple(sorted(own, key=lambda c: c.rank))
    if not selected:
        selected = select_top_candidates(sync.saved, selection.partitions_per_run)
        if claim_for is not None:
            for candidate in selected:
                candidate.claim(claim_for, lease_until, now)
    if selected:
        return CandidatePick(saved=sync.saved, removed=sync.removed, selected=selected)
    leases = [c.lease_expires_at for c in sync.saved if c.state.holds_a_claim and c.lease_expires_at is not None]
    if leases:
        return CandidatePick(
            saved=sync.saved,
            removed=sync.removed,
            shortfall=CandidateShortfall.ALL_CLAIMED,
            next_eligible_at=min(leases),
        )
    return CandidatePick(
        saved=sync.saved,
        removed=sync.removed,
        shortfall=CandidateShortfall.ALL_HELD,
        next_eligible_at=sync.next_check_at,
    )


def _released(
    candidate: CompactionCandidate, released_runs: frozenset[TableMaintenanceRunId], now: datetime
) -> CompactionCandidate:
    run_id = candidate.claimed_by_run_id
    if candidate.state.holds_a_claim and run_id is not None and run_id in released_runs:
        candidate.release(run_id, now)
    return candidate
