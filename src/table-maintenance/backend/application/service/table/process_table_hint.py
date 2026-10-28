"""Define the ProcessTableHintService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.table.table_change import TableChange
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_status import TableStatus
from application.domain.model.table.table_id import TableId
from application.port.inbound.table.process_table_hint import (
    ProcessTableHintUseCase,
    ProcessTableHintUseCaseInput,
    ProcessTableHintUseCaseOutput,
)
from application.port.outbound.table.read_table_metadata import TableMetadataRef
from application.port.outbound.table.send_discovery_request import (
    SendDiscoveryRequestGatewayInput,
)
from application.port.outbound.table.send_table_change import (
    SendTableChangeGatewayInput,
)
from application.service.table.register_discovered_table import (
    register_discovered_table,
)
from application.service.table.registration_outcome import RegistrationOutcome
from application.service.table.table_hint_action import TableHintAction
from application.service.shared.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable

    from application.port.outbound.table.read_table_metadata import (
        ReadTableMetadataGateway,
        TableMetadata,
    )
    from application.port.outbound.table_discovery_settings.table_discovery_settings_repo import (
        TableDiscoverySettingsRepo,
    )
    from application.port.outbound.table_discovery_rule.table_discovery_rules_repo import (
        TableDiscoveryRulesRepo,
    )
    from application.port.outbound.table.tables_repo import (
        TablesRepo,
    )
    from application.port.outbound.table_maintenance_preset.table_maintenance_presets_repo import (
        TableMaintenancePresetsRepo,
    )
    from application.port.outbound.table.send_discovery_request import (
        SendDiscoveryRequestGateway,
    )
    from application.port.outbound.table.send_table_change import (
        SendTableChangeGateway,
    )


class ProcessTableHintService(ProcessTableHintUseCase):
    """React to a catalog event naming a namespace or one table."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        rules_repo: TableDiscoveryRulesRepo,
        presets_repo: TableMaintenancePresetsRepo,
        table_discovery_settings_repo: TableDiscoverySettingsRepo,
        catalog_gateway: ReadTableMetadataGateway,
        table_change_gateway: SendTableChangeGateway,
        discovery_request_gateway: SendDiscoveryRequestGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._rules_repo = rules_repo
        self._presets_repo = presets_repo
        self._table_discovery_settings_repo = table_discovery_settings_repo
        self._catalog_gateway = catalog_gateway
        self._table_change_gateway = table_change_gateway
        self._discovery_request_gateway = discovery_request_gateway
        self._clock = clock

    def execute(
        self, request: ProcessTableHintUseCaseInput
    ) -> ProcessTableHintUseCaseOutput:
        """Handle the hint; ``event_type`` does not change the behaviour."""
        if request.table is None:
            return self._request_discovery(request)
        found = self._catalog_gateway.load_table(
            TableMetadataRef(request.catalog, request.namespace, request.table)
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

    def _handle_found(self, found: TableMetadata) -> TableHintAction:
        now = self._clock()
        table = self._tables_repo.get(TableId(found.table_uuid))
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
        if table.is_enrolled:
            self._table_change_gateway.send(
                SendTableChangeGatewayInput(
                    table_uuid=table.id.value,
                    table_name=table.name.fully_qualified(),
                    change=TableChange.UPDATED.value,
                    is_enrolled=table.is_enrolled,
                )
            )
            if action == TableHintAction.IGNORED:
                action = TableHintAction.SIGNALLED
        return action

    def _register(self, found: TableMetadata, now: datetime) -> TableHintAction:
        if not self._table_discovery_settings_repo.get_settings().enabled:
            return TableHintAction.IGNORED
        name = TableName(found.catalog, found.namespace, found.table)
        stale = self._tables_repo.find_by_name(name)
        outcome = register_discovered_table(
            found,
            self._rules_repo.list_all(),
            self._tables_repo,
            self._presets_repo,
            self._table_change_gateway,
            now,
        )
        if outcome == RegistrationOutcome.REGISTERED:
            if stale is not None:
                self._discovery_request_gateway.send(
                    SendDiscoveryRequestGatewayInput(found.catalog, None)
                )
            return TableHintAction.REGISTERED
        return TableHintAction.IGNORED
