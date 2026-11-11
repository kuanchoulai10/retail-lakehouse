"""Define the ProcessTableHintService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableId,
    TableManagementChange,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.port.inbound.table import (
    ProcessTableHintUseCase,
    ProcessTableHintUseCaseInput,
    ProcessTableHintUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    SendDiscoveryRequestGatewayInput,
    TableMetadataRef,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table.apply_discovery_to_known_table import (
    apply_discovery_to_known_table,
)
from context.table_maintenance.application.service.table.register_discovered_table import (
    register_discovered_table,
)
from context.table_maintenance.application.service.table.registration_outcome import (
    RegistrationOutcome,
)
from context.table_maintenance.application.service.table.table_hint_action import (
    TableHintAction,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendDiscoveryRequestGateway,
        SendTableChangeGateway,
        TableMetadata,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_rules import (
        TableDiscoveryRulesRepo,
    )


class ProcessTableHintService(ProcessTableHintUseCase):
    """React to a catalog event naming a namespace or one table."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        rules_repo: TableDiscoveryRulesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        table_change_gateway: SendTableChangeGateway,
        discovery_request_gateway: SendDiscoveryRequestGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._rules_repo = rules_repo
        self._catalog_gateway = catalog_gateway
        self._table_change_gateway = table_change_gateway
        self._discovery_request_gateway = discovery_request_gateway
        self._clock = clock

    def execute(self, request: ProcessTableHintUseCaseInput) -> ProcessTableHintUseCaseOutput:
        """Handle the hint; ``event_type`` does not change the behaviour.

        A hint naming one table applies the same steps as a discovery pass to that
        table: an unknown one the rules manage is registered, a known one is
        renamed and decided again, and a managed one is signalled ``updated``.
        """
        if request.table is None:
            return self._request_discovery(request)
        found = self._catalog_gateway.load_table(TableMetadataRef(request.catalog, request.namespace, request.table))
        if found is None:
            return self._handle_missing(request)
        with translate_domain_errors():
            action = self._handle_found(found)
        return ProcessTableHintUseCaseOutput(action=action.value)

    def _request_discovery(self, request: ProcessTableHintUseCaseInput) -> ProcessTableHintUseCaseOutput:
        self._discovery_request_gateway.send(SendDiscoveryRequestGatewayInput(request.catalog, request.namespace))
        return ProcessTableHintUseCaseOutput(action=TableHintAction.DISCOVERY_REQUESTED.value)

    def _handle_missing(self, request: ProcessTableHintUseCaseInput) -> ProcessTableHintUseCaseOutput:
        name = TableName(catalog=request.catalog, namespace=request.namespace, table=request.table or "")
        if self._tables_repo.find_by_name(name) is None:
            return ProcessTableHintUseCaseOutput(action=TableHintAction.IGNORED.value)
        self._discovery_request_gateway.send(SendDiscoveryRequestGatewayInput(request.catalog, None))
        return ProcessTableHintUseCaseOutput(action=TableHintAction.DISCOVERY_REQUESTED.value)

    def _handle_found(self, found: TableMetadata) -> TableHintAction:
        now = self._clock()
        table = self._tables_repo.get(TableId(found.table_uuid))
        if table is None:
            return self._register(found, now)
        if table.status == TableStatus.DROPPED:
            return TableHintAction.IGNORED
        name = TableName(catalog=found.catalog, namespace=found.namespace, table=found.table)
        outcome = apply_discovery_to_known_table(
            table,
            name,
            self._rules_repo.get_rules(),
            self._tables_repo,
            self._table_change_gateway,
            TableChange.UPDATED,
            now,
        )
        if outcome.change == TableManagementChange.MANAGED:
            return TableHintAction.MANAGED
        if outcome.change == TableManagementChange.UNMANAGED:
            return TableHintAction.UNMANAGED
        if outcome.renamed:
            return TableHintAction.RENAMED
        return TableHintAction.SIGNALLED if outcome.signalled else TableHintAction.IGNORED

    def _register(self, found: TableMetadata, now: datetime) -> TableHintAction:
        rules = self._rules_repo.get_rules()
        name = TableName(catalog=found.catalog, namespace=found.namespace, table=found.table)
        stale = self._tables_repo.find_by_name(name)
        outcome = register_discovered_table(
            found,
            rules,
            self._tables_repo,
            self._table_change_gateway,
            TableChange.UPDATED,
            now,
        )
        if outcome == RegistrationOutcome.REGISTERED:
            if stale is not None:
                self._discovery_request_gateway.send(SendDiscoveryRequestGatewayInput(found.catalog, None))
            return TableHintAction.REGISTERED
        return TableHintAction.IGNORED
