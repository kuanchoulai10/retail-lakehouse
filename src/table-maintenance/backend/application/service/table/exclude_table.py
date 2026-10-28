"""Define the ExcludeTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.shared.workflow_ids import SIGNAL_STOP
from application.domain.model.table.table import Table
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_status import TableStatus
from application.domain.model.table.table_id import TableId
from application.exceptions import ConflictError, NotFoundError
from application.port.inbound.table.exclude_table import (
    ExcludeTableUseCase,
    ExcludeTableUseCaseInput,
    ExcludeTableUseCaseOutput,
)
from application.port.outbound.table.read_table_metadata import TableMetadataRef
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.table.table_output_fields import (
    table_output_fields,
)
from application.service.shared.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.table.read_table_metadata import (
        ReadTableMetadataGateway,
    )
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class ExcludeTableService(ExcludeTableUseCase):
    """Exclude a table from maintenance by hand."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        signal_gateway: SendTableSignalGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repo, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._catalog_gateway = catalog_gateway
        self._signal_gateway = signal_gateway
        self._clock = clock

    def execute(self, request: ExcludeTableUseCaseInput) -> ExcludeTableUseCaseOutput:
        """Exclude the table, registering it without settings if unknown."""
        now = self._clock()
        with translate_domain_errors():
            name = TableName(request.catalog, request.namespace, request.table)
            found = self._catalog_gateway.load_table(
                TableMetadataRef(request.catalog, request.namespace, request.table)
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
                uuid = TableId(found.table_uuid)
                name = TableName(found.catalog, found.namespace, found.table)
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
        self._signal_gateway.send(
            SendTableSignalGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                signal=SIGNAL_STOP,
            )
        )
        return ExcludeTableUseCaseOutput(**table_output_fields(table))
