"""Define the IncludeTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.shared.workflow_ids import SIGNAL_RESUME
from application.domain.model.table.table import Table
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_status import TableStatus
from application.domain.model.table.table_id import TableId
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)
from application.exceptions import ConflictError, NotFoundError
from application.port.inbound.table.include_table import (
    IncludeTableUseCase,
    IncludeTableUseCaseInput,
    IncludeTableUseCaseOutput,
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
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class IncludeTableService(IncludeTableUseCase):
    """Include a catalog table in maintenance by hand."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        presets_repo: TableMaintenancePresetsRepo,
        catalog_gateway: ReadTableMetadataGateway,
        signal_gateway: SendTableSignalGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._presets_repo = presets_repo
        self._catalog_gateway = catalog_gateway
        self._signal_gateway = signal_gateway
        self._clock = clock

    def execute(self, request: IncludeTableUseCaseInput) -> IncludeTableUseCaseOutput:
        """Register or reactivate the table as MANUAL ACTIVE and start its workflow."""
        found = self._catalog_gateway.load_table(
            TableMetadataRef(request.catalog, request.namespace, request.table)
        )
        if found is None:
            raise NotFoundError(
                f"table {request.catalog}.{request.namespace}.{request.table} "
                "not found in the catalog"
            )
        preset = self._presets_repo.get(TableMaintenancePresetId(request.preset_id))
        if preset is None:
            raise NotFoundError(
                f"table maintenance preset {request.preset_id} not found"
            )
        now = self._clock()
        with translate_domain_errors():
            name = TableName(found.catalog, found.namespace, found.table)
            uuid = TableId(found.table_uuid)
            table = self._tables_repo.get(uuid)
            if table is None:
                table = Table.include_manual(
                    uuid, name, preset.id, preset.settings, now
                )
                self._tables_repo.create(table)
            else:
                if table.status == TableStatus.DROPPED:
                    raise ConflictError(f"table {uuid} is dropped")
                if table.name != name:
                    table.rename(name, now)
                table.include_manually(preset.id, preset.settings, now)
                self._tables_repo.update(table)
        self._signal_gateway.send(
            SendTableSignalGatewayInput(
                table_uuid=uuid.value,
                table_name=name.fully_qualified(),
                signal=SIGNAL_RESUME,
                start_if_missing=True,
            )
        )
        return IncludeTableUseCaseOutput(**table_output_fields(table))
