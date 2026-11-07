"""Define the GetTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.table import (
    GetTableUseCase,
    GetTableUseCaseInput,
    GetTableUseCaseOutput,
)
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts
from context.catalog.application.service.table.table_output_fields import table_output_fields

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import TablesRepo


class GetTableService(GetTableUseCase):
    """Get one Iceberg table with everything the table page shows."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: GetTableUseCaseInput) -> GetTableUseCaseOutput:
        """Return the table or raise NotFoundError."""
        table = self._tables_repo.get(table_id_from_parts(request.catalog, request.namespace, request.name))
        if table is None:
            raise NotFoundError(
                f"table {request.name} not found in namespace {request.namespace} of catalog {request.catalog}"
            )
        return GetTableUseCaseOutput(**table_output_fields(table))
