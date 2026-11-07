"""Define the RenameTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.table import (
    RenameTableUseCase,
    RenameTableUseCaseInput,
    RenameTableUseCaseOutput,
)
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import TablesRepo


class RenameTableService(RenameTableUseCase):
    """Rename an Iceberg table, or move it to another namespace of the same catalog."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: RenameTableUseCaseInput) -> RenameTableUseCaseOutput:
        """Validate both identities, rename, and return where the table now is."""
        source = table_id_from_parts(request.catalog, request.namespace, request.name)
        target = table_id_from_parts(request.catalog, request.target_namespace, request.target_name)
        self._tables_repo.rename(source, target)
        return RenameTableUseCaseOutput(catalog=target.catalog, namespace=list(target.namespace), name=target.name)
