"""Define the ListCompactionRoundsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListCompactionRoundsUseCaseInput:
    """Carry the request: up to ``limit`` rounds, newest first, that started before ``before`` (any when None)."""

    limit: int = 50
    before: datetime | None = None
