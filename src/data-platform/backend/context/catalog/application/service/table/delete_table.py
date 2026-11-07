"""Define the DeleteTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.table import (
    DeleteTableUseCase,
    DeleteTableUseCaseInput,
    DeleteTableUseCaseOutput,
)
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import TablesRepo


class DeleteTableService(DeleteTableUseCase):
    """Drop an Iceberg table from the catalog; its files are never purged."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: DeleteTableUseCaseInput) -> DeleteTableUseCaseOutput:
        """Drop the table; the repo raises NotFoundError for an unknown one."""
        self._tables_repo.delete(table_id_from_parts(request.catalog, request.namespace, request.name))
        return DeleteTableUseCaseOutput()
