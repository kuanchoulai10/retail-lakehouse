"""Define the GetGenericTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.generic_table import (
    GetGenericTableUseCase,
    GetGenericTableUseCaseInput,
    GetGenericTableUseCaseOutput,
)
from context.catalog.application.service.generic_table.generic_table_id_from_parts import (
    generic_table_id_from_parts,
)
from context.catalog.application.service.generic_table.generic_table_output_fields import (
    generic_table_output_fields,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.generic_table import GenericTablesRepo


class GetGenericTableService(GetGenericTableUseCase):
    """Get one generic table."""

    def __init__(self, generic_tables_repo: GenericTablesRepo) -> None:
        """Bind the repo."""
        self._generic_tables_repo = generic_tables_repo

    def execute(self, request: GetGenericTableUseCaseInput) -> GetGenericTableUseCaseOutput:
        """Return the generic table or raise NotFoundError."""
        table = self._generic_tables_repo.get(
            generic_table_id_from_parts(request.catalog, request.namespace, request.name)
        )
        if table is None:
            raise NotFoundError(
                f"generic table {request.name} not found in namespace {request.namespace} of catalog {request.catalog}"
            )
        return GetGenericTableUseCaseOutput(**generic_table_output_fields(table))
