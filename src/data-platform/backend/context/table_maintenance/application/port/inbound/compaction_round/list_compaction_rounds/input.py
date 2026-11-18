"""Define the ListCompactionRoundsUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class ListCompactionRoundsUseCaseInput(UseCaseInput):
    """Carry the request: up to ``limit`` rounds, newest first, that started before ``before`` (any when None)."""

    limit: int = 50
    before: datetime | None = None
