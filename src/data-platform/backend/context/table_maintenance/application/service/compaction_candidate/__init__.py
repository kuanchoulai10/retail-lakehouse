"""Services for the compaction_candidate group."""

from __future__ import annotations

from context.table_maintenance.application.service.compaction_candidate.list_compaction_candidates import (
    ListCompactionCandidatesService,
)
from context.table_maintenance.application.service.compaction_candidate.release_compaction_candidates import (
    ReleaseCompactionCandidatesService,
)

__all__ = [
    "ListCompactionCandidatesService",
    "ReleaseCompactionCandidatesService",
]
