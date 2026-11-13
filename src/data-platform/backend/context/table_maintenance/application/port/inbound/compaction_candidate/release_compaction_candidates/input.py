"""Define the ReleaseCompactionCandidatesUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ReleaseCompactionCandidatesUseCaseInput:
    """Carry the request to hand back the compaction candidates of a run that never started."""

    run_id: str
    now: datetime
