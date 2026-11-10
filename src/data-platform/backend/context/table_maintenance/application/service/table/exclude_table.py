"""Define the ExcludeTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    Table,
    TableChange,
    TableId,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
)
from context.table_maintenance.application.port.inbound.table import (
    ExcludeTableUseCase,
    ExcludeTableUseCaseInput,
    ExcludeTableUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    SendTableChangeGatewayInput,
    TableMetadataRef,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table.table_output_fields import (
    table_output_fields,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendTableChangeGateway,
        TablesRepo,
    )


class ExcludeTableService(ExcludeTableUseCase):
    """Exclude a table from maintenance by hand."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        table_change_gateway: SendTableChangeGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway
        self._table_change_gateway = table_change_gateway
        self._clock = clock

    def execute(self, request: ExcludeTableUseCaseInput) -> ExcludeTableUseCaseOutput:
        """Exclude the table, registering it without settings if unknown."""
        now = self._clock()
        with translate_domain_errors():
            name = TableName(catalog=request.catalog, namespace=request.namespace, table=request.table)
            found = self._catalog_gateway.load_table(
                TableMetadataRef(request.catalog, request.namespace, request.table)
            )
            if found is None:
                table = self._tables_repo.find_by_name(name)
                if table is None:
                    raise NotFoundError(f"table {request.catalog}.{request.namespace}.{request.table} not found")
                table.exclude(now)
                self._tables_repo.update(table)
            else:
                uuid = TableId(found.table_uuid)
                name = TableName(catalog=found.catalog, namespace=found.namespace, table=found.table)
                existing = self._tables_repo.get(uuid)
                if existing is None:
                    table = Table.exclude_manual(uuid, name, now)
                    self._tables_repo.create(table)
                else:
                    table = existing
                    if table.status == TableStatus.DROPPED:
                        raise ConflictError(f"table {uuid} is dropped")
                    if table.name != name:
                        table.rename(name, now)
                    table.exclude(now)
                    self._tables_repo.update(table)
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.STOPPED.value,
                is_enrolled=table.is_enrolled,
            )
        )
        return ExcludeTableUseCaseOutput(**table_output_fields(table))
