"""Define the ListTableReconciliationsUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class ListTableReconciliationsUseCaseInput:
    """Carry the request to list the reconciliations of a table."""

    table_uuid: str
    before: datetime | None = None
    limit: int = 50
