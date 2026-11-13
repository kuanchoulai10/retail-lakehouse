"""Define the CandidatePick value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_shortfall import (
    CandidateShortfall,
)
from context.table_maintenance.application.domain.model.compaction_candidate.compaction_candidate import (
    CompactionCandidate,
)
from context.table_maintenance.application.domain.model.compaction_candidate.compaction_candidate_id import (
    CompactionCandidateId,
)


class CandidatePick(ValueObject):
    """Say how one plan changes a table's candidates and which of them its run compacts.

    ``saved`` and ``removed`` are what to store, as for a sync. ``selected`` are
    the candidates the run compacts, best first (empty when compaction is not due
    or nothing can be taken). ``shortfall`` says why a due compaction took nothing,
    and ``next_eligible_at`` when that may change (None when only a new write or
    a policy change can).
    """

    saved: tuple[CompactionCandidate, ...]
    removed: tuple[CompactionCandidateId, ...]
    selected: tuple[CompactionCandidate, ...] = ()
    shortfall: CandidateShortfall | None = None
    next_eligible_at: datetime | None = None
