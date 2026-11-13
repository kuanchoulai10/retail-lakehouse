"""Compaction candidate domain vocabulary: the partitions worth compacting and their scores."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.compaction_candidate.candidate_score import (
    CandidateScore,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_state import (
    CandidateState,
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
from context.table_maintenance.application.domain.model.compaction_candidate.partition_key import (
    PartitionKey,
)

__all__ = [
    "CandidateScore",
    "CandidateState",
    "CompactionCandidate",
    "CompactionCandidateId",
    "HoldReason",
    "InvalidCandidateTransition",
    "PartitionKey",
]
