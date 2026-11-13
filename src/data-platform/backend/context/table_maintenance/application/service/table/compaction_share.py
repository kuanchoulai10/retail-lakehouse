"""Define the CompactionShare result of a plan's candidate pick."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.compaction_candidate import CompactionCandidate
    from context.table_maintenance.application.domain.model.shared import ComputeSize


@dataclass(frozen=True)
class CompactionShare:
    """What a scheduled plan's compaction takes: its candidates and start size, or when to look again."""

    candidates: tuple[CompactionCandidate, ...] = ()
    start_size: ComputeSize | None = None
    next_check_at: datetime | None = None
