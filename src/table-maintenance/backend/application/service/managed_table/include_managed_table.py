"""Define the IncludeManagedTableService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import SIGNAL_RESUME
from application.domain.model.managed_table.managed_table import ManagedTable
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_status import TableStatus
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import ConflictError, NotFoundError
from application.port.inbound.managed_table.include_managed_table import (
    IncludeManagedTableUseCase,
    IncludeManagedTableUseCaseInput,
    IncludeManagedTableUseCaseOutput,
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
    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class IncludeManagedTableService(IncludeManagedTableUseCase):
    """Include a catalog table in maintenance by hand."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: ManagedTablesRepo,
        templates_repo: PolicyTemplatesRepo,
        catalog_gateway: ReadCatalogGateway,
        signal_gateway: SendTableSignalGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._templates_repo = templates_repo
        self._catalog_gateway = catalog_gateway
        self._signal_gateway = signal_gateway
        self._clock = clock

    def execute(
        self, request: IncludeManagedTableUseCaseInput
    ) -> IncludeManagedTableUseCaseOutput:
        """Register or reactivate the table as MANUAL ACTIVE and start its workflow."""
        found = self._catalog_gateway.load_table(
            ReadCatalogGatewayTableRef(
                request.catalog, request.namespace, request.table
            )
        )
        if found is None:
            raise NotFoundError(
                f"table {request.catalog}.{request.namespace}.{request.table} "
                "not found in the catalog"
            )
        template = self._templates_repo.get(PolicyTemplateId(request.template_id))
        if template is None:
            raise NotFoundError(f"policy template {request.template_id} not found")
        now = self._clock()
        with translate_domain_errors():
            name = TableName(found.catalog, found.namespace, found.table)
            uuid = TableUuid(found.table_uuid)
            table = self._tables_repo.get(uuid)
            if table is None:
                table = ManagedTable.include_manual(
                    uuid, name, template.id, template.settings, now
                )
                self._tables_repo.create(table)
            else:
                if table.status == TableStatus.DROPPED:
                    raise ConflictError(f"managed table {uuid} is dropped")
                if table.name != name:
                    table.rename(name, now)
                table.include_manually(template.id, template.settings, now)
                self._tables_repo.update(table)
        self._signal_gateway.send(
            SendTableSignalGatewayInput(
                table_uuid=uuid.value,
                table_name=name.fully_qualified(),
                signal=SIGNAL_RESUME,
                start_if_missing=True,
            )
        )
        return IncludeManagedTableUseCaseOutput(**managed_table_output_fields(table))
