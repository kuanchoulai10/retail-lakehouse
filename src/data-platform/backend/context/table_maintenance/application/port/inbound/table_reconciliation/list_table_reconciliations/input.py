"""Define the ListTableReconciliationsUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class ListTableReconciliationsUseCaseInput(UseCaseInput):
    """Carry the request to list the reconciliations of a table."""

    table_uuid: str
    before: datetime | None = None
    limit: int = 50
