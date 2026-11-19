"""Define the SetTablePriorityService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TablePriority
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table import (
    SetTablePriorityUseCase,
    SetTablePriorityUseCaseInput,
    SetTablePriorityUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table import TablesRepo


class SetTablePriorityService(SetTablePriorityUseCase):
    """Set the priority of a table and save it."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: SetTablePriorityUseCaseInput) -> SetTablePriorityUseCaseOutput:
        """Set the priority, or raise ValidationError, NotFoundError or ConflictError (a dropped table)."""
        try:
            priority = TablePriority(request.priority)
        except ValueError as exc:
            raise ValidationError(f"unknown priority {request.priority!r}; expected one of P0, P1, P2, P3") from exc
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        with translate_domain_errors():
            table.set_priority(priority, request.now)
            self._tables_repo.update(table)
        return SetTablePriorityUseCaseOutput(uuid=table.id.value, priority=table.priority.value)
