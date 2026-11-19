"""Define the SetTablePriorityUseCaseInput."""

from __future__ import annotations

from datetime import datetime

from base import UseCaseInput


class SetTablePriorityUseCaseInput(UseCaseInput):
    """Carry the request to set a table's priority."""

    uuid: str
    priority: str
    now: datetime
