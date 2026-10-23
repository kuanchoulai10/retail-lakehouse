"""Define the ListManagedTablesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.managed_table.table_status import TableStatus
from application.port.inbound.managed_table.list_managed_tables import (
    ListManagedTablesUseCase,
    ListManagedTablesUseCaseInput,
    ListManagedTablesUseCaseOutput,
    ListManagedTablesUseCaseOutputItem,
)
from application.service.managed_table.managed_table_output_fields import (
    managed_table_output_fields,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )


class ListManagedTablesService(ListManagedTablesUseCase):
    """List managed tables, optionally filtered by status."""

    def __init__(self, tables_repo: ManagedTablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(
        self, request: ListManagedTablesUseCaseInput
    ) -> ListManagedTablesUseCaseOutput:
        """Return the tables, all of them when no status is given."""
        if request.status is None:
            tables = self._tables_repo.list_all()
        else:
            with translate_domain_errors():
                status = TableStatus(request.status)
            tables = self._tables_repo.list_by_statuses([status])
        return ListManagedTablesUseCaseOutput(
            items=[
                ListManagedTablesUseCaseOutputItem(**managed_table_output_fields(t))
                for t in tables
            ]
        )
