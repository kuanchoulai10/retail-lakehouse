"""Define the select_top_candidates domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import CandidateState

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.compaction_candidate import CompactionCandidate


def select_top_candidates(candidates: Sequence[CompactionCandidate], n: int) -> tuple[CompactionCandidate, ...]:
    """Return the ``n`` best pending candidates, best first (see ``CompactionCandidate.rank``)."""
    pending = [c for c in candidates if c.state is CandidateState.PENDING]
    ranked = sorted(pending, key=lambda c: c.rank)
    return tuple(ranked[: max(0, n)])
