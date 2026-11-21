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
from context.table_maintenance.application.service.table.attention_policy_names import (
    attention_policy_names,
)
from context.table_maintenance.application.service.table.table_output_fields import (
    table_output_fields,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.port.outbound.catalog_discovery import (
        CatalogDiscoveriesRepo,
    )
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_policy import (
        TableMaintenancePoliciesRepo,
    )


class ListTablesService(ListTablesUseCase):
    """List tables, optionally filtered by status."""

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

    def execute(self, request: ListTablesUseCaseInput) -> ListTablesUseCaseOutput:
        """Return the tables, all of them when no status is given, with each one's last commit and discovery."""
        if request.status is None:
            tables = self._tables_repo.list_all()
        else:
            with translate_domain_errors():
                status = TableStatus(request.status)
            tables = self._tables_repo.list_by_statuses([status])
        discovered: dict[str, datetime | None] = {
            d.catalog: d.last_discovered_at for d in self._discoveries_repo.list_all()
        }
        names = attention_policy_names(tables, self._policies_repo)
        return ListTablesUseCaseOutput(
            items=tuple(
                ListTablesUseCaseOutput.Table(**table_output_fields(t, discovered.get(t.name.catalog), names))
                for t in tables
            )
        )
