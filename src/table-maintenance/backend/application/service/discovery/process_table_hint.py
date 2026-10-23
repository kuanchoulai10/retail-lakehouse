"""Define the ProcessTableHintService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import SIGNAL_TABLE_UPDATED
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_status import TableStatus
from application.domain.model.managed_table.table_uuid import TableUuid
from application.port.inbound.discovery.process_table_hint import (
    ProcessTableHintUseCase,
    ProcessTableHintUseCaseInput,
    ProcessTableHintUseCaseOutput,
)
from application.port.outbound.catalog.read_catalog import ReadCatalogGatewayTableRef
from application.port.outbound.workflow.send_discovery_request import (
    SendDiscoveryRequestGatewayInput,
)
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.discovery.register_discovered_table import (
    register_discovered_table,
)
from application.service.discovery.registration_outcome import RegistrationOutcome
from application.service.discovery.table_hint_action import TableHintAction
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.catalog.read_catalog import (
        ReadCatalogGateway,
        ReadCatalogGatewayTable,
    )
    from application.port.outbound.discovery.discovery_settings_repo import (
        DiscoverySettingsRepo,
    )
    from application.port.outbound.discovery_rule.discovery_rules_repo import (
        DiscoveryRulesRepo,
    )
    from application.port.outbound.managed_table.managed_tables_repo import (
        ManagedTablesRepo,
    )
    from application.port.outbound.policy_template.policy_templates_repo import (
        PolicyTemplatesRepo,
    )
    from application.port.outbound.workflow.send_discovery_request import (
        SendDiscoveryRequestGateway,
    )
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )


class ProcessTableHintService(ProcessTableHintUseCase):
    """React to a catalog event naming a namespace or one table."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: ManagedTablesRepo,
        rules_repo: DiscoveryRulesRepo,
        templates_repo: PolicyTemplatesRepo,
        discovery_settings_repo: DiscoverySettingsRepo,
        catalog_gateway: ReadCatalogGateway,
        signal_gateway: SendTableSignalGateway,
        discovery_request_gateway: SendDiscoveryRequestGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._rules_repo = rules_repo
        self._templates_repo = templates_repo
        self._discovery_settings_repo = discovery_settings_repo
        self._catalog_gateway = catalog_gateway
        self._signal_gateway = signal_gateway
        self._discovery_request_gateway = discovery_request_gateway
        self._clock = clock

    def execute(
        self, request: ProcessTableHintUseCaseInput
    ) -> ProcessTableHintUseCaseOutput:
        """Handle the hint; ``event_type`` does not change the behaviour."""
        if request.table is None:
            return self._request_discovery(request)
        found = self._catalog_gateway.load_table(
            ReadCatalogGatewayTableRef(
                request.catalog, request.namespace, request.table
            )
        )
        if found is None:
            return self._handle_missing(request)
        with translate_domain_errors():
            action = self._handle_found(found)
        return ProcessTableHintUseCaseOutput(action=action.value)

    def _request_discovery(
        self, request: ProcessTableHintUseCaseInput
    ) -> ProcessTableHintUseCaseOutput:
        self._discovery_request_gateway.send(
            SendDiscoveryRequestGatewayInput(request.catalog, request.namespace)
        )
        return ProcessTableHintUseCaseOutput(
            action=TableHintAction.DISCOVERY_REQUESTED.value
        )

    def _handle_missing(
        self, request: ProcessTableHintUseCaseInput
    ) -> ProcessTableHintUseCaseOutput:
        name = TableName(request.catalog, request.namespace, request.table or "")
        if self._tables_repo.find_by_name(name) is None:
            return ProcessTableHintUseCaseOutput(action=TableHintAction.IGNORED.value)
        self._discovery_request_gateway.send(
            SendDiscoveryRequestGatewayInput(request.catalog, None)
        )
        return ProcessTableHintUseCaseOutput(
            action=TableHintAction.DISCOVERY_REQUESTED.value
        )

    def _handle_found(self, found: ReadCatalogGatewayTable) -> TableHintAction:
        now = self._clock()
        table = self._tables_repo.get(TableUuid(found.table_uuid))
        if table is None:
            return self._register(found, now)
        if table.status == TableStatus.DROPPED:
            return TableHintAction.IGNORED
        action = TableHintAction.IGNORED
        name = TableName(found.catalog, found.namespace, found.table)
        if table.name != name:
            table.rename(name, now)
            self._tables_repo.update(table)
            action = TableHintAction.RENAMED
        if table.needs_reconcile_workflow:
            self._signal_gateway.send(
                SendTableSignalGatewayInput(
                    table_uuid=table.id.value, signal=SIGNAL_TABLE_UPDATED
                )
            )
            if action == TableHintAction.IGNORED:
                action = TableHintAction.SIGNALLED
        return action

    def _register(
        self, found: ReadCatalogGatewayTable, now: datetime
    ) -> TableHintAction:
        if not self._discovery_settings_repo.get_settings().enabled:
            return TableHintAction.IGNORED
        name = TableName(found.catalog, found.namespace, found.table)
        stale = self._tables_repo.find_by_name(name)
        outcome = register_discovered_table(
            found,
            self._rules_repo.list_all(),
            self._tables_repo,
            self._templates_repo,
            self._signal_gateway,
            now,
        )
        if outcome == RegistrationOutcome.REGISTERED:
            if stale is not None:
                self._discovery_request_gateway.send(
                    SendDiscoveryRequestGatewayInput(found.catalog, None)
                )
            return TableHintAction.REGISTERED
        return TableHintAction.IGNORED
