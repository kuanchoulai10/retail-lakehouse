"""Define the ExcludeManagedTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import SIGNAL_STOP
from application.domain.model.managed_table.managed_table import ManagedTable
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_status import TableStatus
from application.domain.model.managed_table.table_uuid import TableUuid
from application.exceptions import ConflictError, NotFoundError
from application.port.inbound.managed_table.exclude_managed_table import (
    ExcludeManagedTableUseCase,
    ExcludeManagedTableUseCaseInput,
    ExcludeManagedTableUseCaseOutput,
)
from application.port.outbound.catalog.read_catalog import ReadCatalogGatewayTableRef
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.managed_table.managed_table_output_fields import (
    managed_table_output_fields,
)
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.catalog.read_catalog import ReadCatalogGateway
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class ExcludeManagedTableService(ExcludeManagedTableUseCase):
    """Exclude a table from maintenance by hand."""

    def __init__(
        self,
        tables_repo: ManagedTablesRepo,
        catalog_gateway: ReadCatalogGateway,
        signal_gateway: SendTableSignalGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway
        self._signal_gateway = signal_gateway
        self._clock = clock

    def execute(
        self, request: ExcludeManagedTableUseCaseInput
    ) -> ExcludeManagedTableUseCaseOutput:
        """Exclude the table, registering it without settings if unknown."""
        now = self._clock()
        with translate_domain_errors():
            name = TableName(request.catalog, request.namespace, request.table)
            found = self._catalog_gateway.load_table(
                ReadCatalogGatewayTableRef(
                    request.catalog, request.namespace, request.table
                )
            )
            if found is None:
                table = self._tables_repo.find_by_name(name)
                if table is None:
                    raise NotFoundError(
                        f"table {request.catalog}.{request.namespace}.{request.table} "
                        "not found"
                    )
                table.exclude(now)
                self._tables_repo.update(table)
            else:
                uuid = TableUuid(found.table_uuid)
                name = TableName(found.catalog, found.namespace, found.table)
                existing = self._tables_repo.get(uuid)
                if existing is None:
                    table = ManagedTable.exclude_manual(uuid, name, now)
                    self._tables_repo.create(table)
                else:
                    table = existing
                    if table.status == TableStatus.DROPPED:
                        raise ConflictError(f"managed table {uuid} is dropped")
                    if table.name != name:
                        table.rename(name, now)
                    table.exclude(now)
                    self._tables_repo.update(table)
        self._signal_gateway.send(
            SendTableSignalGatewayInput(table_uuid=table.id.value, signal=SIGNAL_STOP)
        )
        return ExcludeManagedTableUseCaseOutput(**managed_table_output_fields(table))
