"""Define the ListTableCommitsUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class ListTableCommitsUseCaseInput(UseCaseInput):
    """Carry the request to list the commits of one table."""

    uuid: str
    limit: int = 100
    since: datetime | None = None
    before: datetime | None = None
    writer: str | None = None
