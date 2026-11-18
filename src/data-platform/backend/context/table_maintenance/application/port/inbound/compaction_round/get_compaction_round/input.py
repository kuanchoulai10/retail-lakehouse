"""Define the GetCompactionRoundUseCaseInput."""

from __future__ import annotations

from base import UseCaseInput


class GetCompactionRoundUseCaseInput(UseCaseInput):
    """Carry the request: the compaction round ``round_id``."""

    round_id: str
