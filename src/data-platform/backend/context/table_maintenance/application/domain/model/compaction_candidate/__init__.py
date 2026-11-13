"""Compaction candidate domain vocabulary: the partitions worth compacting and their scores."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.compaction_candidate.candidate_filters import (
    CandidateFilters,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_pick import (
    CandidatePick,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_score import (
    CandidateScore,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_scoring import (
    CandidateScoring,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_selection import (
    CandidateSelection,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_shortfall import (
    CandidateShortfall,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_state import (
    CandidateState,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_sync import (
    CandidateSync,
)
from context.table_maintenance.application.domain.model.compaction_candidate.compaction_candidate import (
    CompactionCandidate,
)
from context.table_maintenance.application.domain.model.compaction_candidate.compaction_candidate_id import (
    CompactionCandidateId,
)
from context.table_maintenance.application.domain.model.compaction_candidate.hold_reason import (
    HoldReason,
)
from context.table_maintenance.application.domain.model.compaction_candidate.invalid_candidate_transition import (
    InvalidCandidateTransition,
)
from context.table_maintenance.application.domain.model.compaction_candidate.observed_partition import (
    ObservedPartition,
)
from context.table_maintenance.application.domain.model.compaction_candidate.partition_key import (
    PartitionKey,
)
from context.table_maintenance.application.domain.model.compaction_candidate.stale_compaction_candidate import (
    StaleCompactionCandidate,
)

__all__ = [
    "ObservedPartition",
    "CandidateSync",
    "CandidateScoring",
    "CandidateFilters",
    "CandidatePick",
    "CandidateScore",
    "CandidateShortfall",
    "CandidateSelection",
    "CandidateState",
    "CompactionCandidate",
    "CompactionCandidateId",
    "HoldReason",
    "InvalidCandidateTransition",
    "PartitionKey",
    "StaleCompactionCandidate",
]
