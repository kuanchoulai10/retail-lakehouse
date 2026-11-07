"""Define the ListTablesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table import TableStatus
from application.port.inbound.table import (
    ListTablesUseCase,
    ListTablesUseCaseInput,
    ListTablesUseCaseOutput,
    ListTablesUseCaseOutputItem,
)
from application.service.table.table_output_fields import (
    table_output_fields,
)
from application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from application.port.outbound.table import TablesRepo


class ListTablesService(ListTablesUseCase):
    """List tables, optionally filtered by status."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: ListTablesUseCaseInput) -> ListTablesUseCaseOutput:
        """Return the tables, all of them when no status is given."""
        if request.status is None:
            tables = self._tables_repo.list_all()
        else:
            with translate_domain_errors():
                status = TableStatus(request.status)
            tables = self._tables_repo.list_by_statuses([status])
        return ListTablesUseCaseOutput(
            items=[
                ListTablesUseCaseOutputItem(**table_output_fields(t)) for t in tables
            ]
        )
