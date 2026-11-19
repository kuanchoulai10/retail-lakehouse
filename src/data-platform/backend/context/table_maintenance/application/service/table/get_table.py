"""Define the GetTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.catalog_discovery import CatalogDiscoveryId
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.table import (
    GetTableUseCase,
    GetTableUseCaseInput,
    GetTableUseCaseOutput,
)
from context.table_maintenance.application.service.table.attention_policy_names import (
    attention_policy_names,
)
from context.table_maintenance.application.service.table.table_output_fields import (
    table_output_fields,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.catalog_discovery import (
        CatalogDiscoveriesRepo,
    )
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class GetTableService(GetTableUseCase):
    """Get one table with its settings and operation states."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        discoveries_repo: CatalogDiscoveriesRepo,
        policies_repo: TableMaintenancePoliciesRepo,
    ) -> None:
        """Bind the repos; the policies repo gives the current name of a policy a mark points at."""
        self._tables_repo = tables_repo
        self._discoveries_repo = discoveries_repo
        self._policies_repo = policies_repo

    def execute(self, request: GetTableUseCaseInput) -> GetTableUseCaseOutput:
        """Return the table or raise NotFoundError."""
        table = self._tables_repo.get(TableId(request.uuid))
        if table is None:
            raise NotFoundError(f"table {request.uuid} not found")
        discovery = self._discoveries_repo.get(CatalogDiscoveryId(table.name.catalog))
        discovered_at = None if discovery is None else discovery.last_discovered_at
        names = attention_policy_names([table], self._policies_repo)
        return GetTableUseCaseOutput(**table_output_fields(table, discovered_at, names))
