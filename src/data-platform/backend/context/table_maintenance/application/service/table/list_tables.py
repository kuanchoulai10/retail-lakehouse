"""Define the ListTablesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import TableStatus
from context.table_maintenance.application.port.inbound.table import (
    ListTablesUseCase,
    ListTablesUseCaseInput,
    ListTablesUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table.table_output_fields import (
    table_output_fields,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.port.outbound.catalog_discovery import (
        CatalogDiscoveriesRepo,
    )
    from context.table_maintenance.application.port.outbound.table import TablesRepo


class ListTablesService(ListTablesUseCase):
    """List tables, optionally filtered by status."""

    def __init__(self, tables_repo: TablesRepo, discoveries_repo: CatalogDiscoveriesRepo) -> None:
        """Bind the repos."""
        self._tables_repo = tables_repo
        self._discoveries_repo = discoveries_repo

    def execute(self, request: ListTablesUseCaseInput) -> ListTablesUseCaseOutput:
        """Return the tables, all of them when no status is given, with each one's last commit and discovery."""
        if request.status is None:
            tables = self._tables_repo.list_all()
        else:
            with translate_domain_errors():
                status = TableStatus(request.status)
            tables = self._tables_repo.list_by_statuses([status])
        discovered: dict[str, datetime] = {d.catalog: d.last_discovered_at for d in self._discoveries_repo.list_all()}
        return ListTablesUseCaseOutput(
            items=tuple(
                ListTablesUseCaseOutput.Table(**table_output_fields(t, discovered.get(t.name.catalog))) for t in tables
            )
        )
