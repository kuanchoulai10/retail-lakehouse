"""Outbound ports for the compaction_candidate group."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    CompactionCandidateId,
    HoldReason,
    PartitionKey,
    StaleCompactionCandidate,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    TableMaintenanceRunId,
)
from context.table_maintenance.application.port.outbound.compaction_candidate.compaction_candidates_repo import (
    CompactionCandidatesRepo,
)

__all__ = [
    "CandidateScore",
    "CandidateState",
    "CompactionCandidate",
    "CompactionCandidateId",
    "CompactionCandidatesRepo",
    "HoldReason",
    "MaintenancePriority",
    "PartitionKey",
    "StaleCompactionCandidate",
    "TableId",
    "TableMaintenanceRunId",
]
