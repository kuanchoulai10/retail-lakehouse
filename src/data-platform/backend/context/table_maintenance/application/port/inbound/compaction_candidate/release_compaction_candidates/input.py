"""Define the ReleaseCompactionCandidatesUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class ReleaseCompactionCandidatesUseCaseInput(UseCaseInput):
    """Carry the request to hand back the compaction candidates of a run that never started."""

    run_id: str
    now: datetime
