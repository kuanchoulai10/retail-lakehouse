"""Define the CandidateSync value object."""

from __future__ import annotations

from datetime import datetime

from base import ValueObject
from context.table_maintenance.application.domain.model.compaction_candidate.compaction_candidate import (
    CompactionCandidate,
)
from context.table_maintenance.application.domain.model.compaction_candidate.compaction_candidate_id import (
    CompactionCandidateId,
)


class CandidateSync(ValueObject):
    """Say how one observation changes a table's candidates.

    ``saved`` are the created and updated candidates, ``removed`` the ids of those
    whose partitions no longer need compaction, and ``next_check_at`` the earliest
    moment a recently-written hold ends (None when nothing is held for that).
    """

    saved: tuple[CompactionCandidate, ...]
    removed: tuple[CompactionCandidateId, ...]
    next_check_at: datetime | None = None
