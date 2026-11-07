"""Define the DeleteGenericTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.generic_table import (
    DeleteGenericTableUseCase,
    DeleteGenericTableUseCaseInput,
    DeleteGenericTableUseCaseOutput,
)
from context.catalog.application.service.generic_table.generic_table_id_from_parts import (
    generic_table_id_from_parts,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.generic_table import GenericTablesRepo


class DeleteGenericTableService(DeleteGenericTableUseCase):
    """Drop a generic table from the catalog."""

    def __init__(self, generic_tables_repo: GenericTablesRepo) -> None:
        """Bind the repo."""
        self._generic_tables_repo = generic_tables_repo

    def execute(self, request: DeleteGenericTableUseCaseInput) -> DeleteGenericTableUseCaseOutput:
        """Drop the generic table; the repo raises NotFoundError for an unknown one."""
        self._generic_tables_repo.delete(generic_table_id_from_parts(request.catalog, request.namespace, request.name))
        return DeleteGenericTableUseCaseOutput()
