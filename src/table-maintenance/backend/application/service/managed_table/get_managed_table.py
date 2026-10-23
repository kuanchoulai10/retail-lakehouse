"""Define the GetManagedTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.managed_table.table_uuid import TableUuid
from application.exceptions import NotFoundError
from application.port.inbound.managed_table.get_managed_table import (
    GetManagedTableUseCase,
    GetManagedTableUseCaseInput,
    GetManagedTableUseCaseOutput,
)
from application.service.managed_table.managed_table_output_fields import (
    managed_table_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )


class GetManagedTableService(GetManagedTableUseCase):
    """Get one managed table with its settings and operation states."""

    def __init__(self, tables_repo: ManagedTablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(
        self, request: GetManagedTableUseCaseInput
    ) -> GetManagedTableUseCaseOutput:
        """Return the table or raise NotFoundError."""
        table = self._tables_repo.get(TableUuid(request.uuid))
        if table is None:
            raise NotFoundError(f"managed table {request.uuid} not found")
        return GetManagedTableUseCaseOutput(**managed_table_output_fields(table))
