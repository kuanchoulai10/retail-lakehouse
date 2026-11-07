"""Define the SyncDiscoveredTablesService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableId,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table import (
    SyncDiscoveredTablesUseCase,
    SyncDiscoveredTablesUseCaseInput,
    SyncDiscoveredTablesUseCaseOutput,
)
from context.table_maintenance.application.port.outbound.table import (
    ReadTableMetadataGatewayListInput,
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table.register_discovered_table import (
    register_discovered_table,
)
from context.table_maintenance.application.service.table.registration_outcome import (
    RegistrationOutcome,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.domain.model.table_discovery_rule import (
        TableDiscoveryRule,
    )
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendTableChangeGateway,
        TableMetadata,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_rule import (
        TableDiscoveryRulesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_settings import (
        TableDiscoverySettingsRepo,
    )
    from context.table_maintenance.application.port.outbound.table_maintenance_preset import (
        TableMaintenancePresetsRepo,
    )

_REGISTERED = "registered"
_RENAMED = "renamed"
_SKIPPED = "skipped"
_DROP_SCAN_STATUSES = (TableStatus.ACTIVE, TableStatus.PAUSED, TableStatus.EXCLUDED)


class SyncDiscoveredTablesService(SyncDiscoveredTablesUseCase):
    """Make the registry match the tables currently in the catalog."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        rules_repo: TableDiscoveryRulesRepo,
        presets_repo: TableMaintenancePresetsRepo,
        table_discovery_settings_repo: TableDiscoverySettingsRepo,
        catalog_gateway: ReadTableMetadataGateway,
        table_change_gateway: SendTableChangeGateway,
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
        self._clock = clock

    def execute(self, request: SyncDiscoveredTablesUseCaseInput) -> SyncDiscoveredTablesUseCaseOutput:
        """Register, rename and drop tables within the catalog or namespace scope.

        New tables are registered only while discovery is enabled; renames always run.
        Only a catalog-wide sync (no namespace) marks missing tables dropped, since
        a namespace scan cannot tell a drop from a move. Known tables are never
        re-decided, and a table that fails is counted in ``skipped``. A
        catalog-wide sync also signal-with-starts the reconciliation workflow of every
        known live table that needs one (counted in ``ensured``), so a table whose
        workflow was never started, or was lost, is picked up again.
        """
        now = self._clock()
        enabled = self._table_discovery_settings_repo.get_settings().enabled
        rules = self._rules_repo.list_all() if enabled else []
        refs = self._catalog_gateway.list_tables(ReadTableMetadataGatewayListInput(request.catalog, request.namespace))
        seen: set[str] = set()
        registered = renamed = skipped = ensured = 0
        for ref in refs:
            found = self._catalog_gateway.load_table(ref)
            if found is None:
                continue
            seen.add(found.table_uuid)
            try:
                with translate_domain_errors():
                    outcome, existing = self._sync_table(found, enabled, rules, now)
            except ConflictError, ValidationError, NotFoundError:
                skipped += 1
                continue
            registered += outcome == _REGISTERED
            renamed += outcome == _RENAMED
            skipped += outcome == _SKIPPED
            if request.namespace is None and existing is not None:
                ensured += self._ensure_enrolled(existing)
        dropped = 0
        if request.namespace is None:
            with translate_domain_errors():
                dropped = self._drop_missing(request, seen, now)
        return SyncDiscoveredTablesUseCaseOutput(
            registered=registered,
            renamed=renamed,
            dropped=dropped,
            skipped=skipped,
            ensured=ensured,
        )

    def _sync_table(
        self,
        found: TableMetadata,
        enabled: bool,
        rules: Sequence[TableDiscoveryRule],
        now: datetime,
    ) -> tuple[str, Table | None]:
        existing = self._tables_repo.get(TableId(found.table_uuid))
        if existing is None:
            if not enabled:
                return "", None
            outcome = register_discovered_table(
                found,
                rules,
                self._tables_repo,
                self._presets_repo,
                self._table_change_gateway,
                now,
            )
            if outcome == RegistrationOutcome.REGISTERED:
                return _REGISTERED, None
            return (_SKIPPED if outcome == RegistrationOutcome.SKIPPED else ""), None
        name = TableName(found.catalog, found.namespace, found.table)
        if existing.status != TableStatus.DROPPED and existing.name != name:
            existing.rename(name, now)
            self._tables_repo.update(existing)
            return _RENAMED, existing
        return "", existing

    def _ensure_enrolled(self, table: Table) -> bool:
        """Tell the runtime an enrolled table was seen, so it is kept under maintenance."""
        if not table.is_enrolled:
            return False
        self._table_change_gateway.send(
            SendTableChangeGatewayInput(
                table_uuid=table.id.value,
                table_name=table.name.fully_qualified(),
                change=TableChange.UPDATED.value,
                is_enrolled=table.is_enrolled,
            )
        )
        return True

    def _drop_missing(
        self,
        request: SyncDiscoveredTablesUseCaseInput,
        seen: set[str],
        now: datetime,
    ) -> int:
        dropped = 0
        for table in self._tables_repo.list_by_statuses(_DROP_SCAN_STATUSES):
            if table.id.value in seen or not _in_scope(table.name, request):
                continue
            was_enrolled = table.is_enrolled
            table.mark_dropped(now)
            self._tables_repo.update(table)
            dropped += 1
            if was_enrolled:
                self._table_change_gateway.send(
                    SendTableChangeGatewayInput(
                        table_uuid=table.id.value,
                        table_name=table.name.fully_qualified(),
                        change=TableChange.STOPPED.value,
                        is_enrolled=table.is_enrolled,
                    )
                )
        return dropped


def _in_scope(name: TableName, request: SyncDiscoveredTablesUseCaseInput) -> bool:
    if name.catalog != request.catalog:
        return False
    return request.namespace is None or name.namespace == request.namespace
