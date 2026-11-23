"""Define the SetTablePriorityService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import TableId, TablePriority
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.inbound.table import (
    SetTablePriorityUseCase,
    SetTablePriorityUseCaseInput,
    SetTablePriorityUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import TablesRepo


class SetTablePriorityService(SetTablePriorityUseCase):
    """Set the priority of a table and save it."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo and the clock."""
        self._tables_repo = tables_repo
        self._clock = clock

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
            changed = table.priority != priority
            table.set_priority(priority, self._clock())
            if changed:
                self._tables_repo.update(table)
        return SetTablePriorityUseCaseOutput(uuid=table.id.value, priority=table.priority.value)
