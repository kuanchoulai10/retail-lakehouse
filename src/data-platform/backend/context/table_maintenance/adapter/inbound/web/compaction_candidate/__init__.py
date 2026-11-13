"""Web adapter for the compaction_candidate group."""

from __future__ import annotations

from context.table_maintenance.adapter.inbound.web.compaction_candidate.dto import (
    CandidatePartitionApiResponse,
    CompactionCandidateApiResponse,
    CompactionCandidatesApiResponse,
)
from context.table_maintenance.adapter.inbound.web.compaction_candidate.router import (
    router,
)

__all__ = [
    "CandidatePartitionApiResponse",
    "CompactionCandidateApiResponse",
    "CompactionCandidatesApiResponse",
    "router",
]
