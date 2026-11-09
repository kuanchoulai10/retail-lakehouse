"""Define the ListTableCommitsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListTableCommitsUseCaseInput:
    """Carry the request to list the commits of one table."""

    uuid: str
    limit: int = 100
    since: datetime | None = None
    before: datetime | None = None
    writer: str | None = None
