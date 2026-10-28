"""Define the GetTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.table import TableId
from application.exceptions import NotFoundError
from application.port.inbound.table import (
    GetTableUseCase,
    GetTableUseCaseInput,
    GetTableUseCaseOutput,
)
from application.service.table.table_output_fields import (
    table_output_fields,
)

if TYPE_CHECKING:
    from application.port.outbound.table import TablesRepo


class GetTableService(GetTableUseCase):
    """Get one table with its settings and operation states."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: GetTableUseCaseInput) -> GetTableUseCaseOutput:
        """Return the table or raise NotFoundError."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        return GetTableUseCaseOutput(**table_output_fields(table))
