"""Define the GetCompactionRoundUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetCompactionRoundUseCaseInput:
    """Carry the request: the compaction round ``round_id``."""

    round_id: str
