"""Define the SetTablePriorityUseCaseOutput."""

from __future__ import annotations

from base import UseCaseOutput


class SetTablePriorityUseCaseOutput(UseCaseOutput):
    """Report the table's priority after the change."""

    uuid: str
    priority: str
