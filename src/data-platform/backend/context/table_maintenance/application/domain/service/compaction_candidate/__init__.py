"""Domain services of the compaction_candidate group."""

from __future__ import annotations

from context.table_maintenance.application.domain.service.compaction_candidate.score_candidate import (
    score_candidate,
)
from context.table_maintenance.application.domain.service.compaction_candidate.sync_compaction_candidates import (
    sync_compaction_candidates,
)

__all__ = [
    "score_candidate",
    "sync_compaction_candidates",
]
