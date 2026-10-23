"""Define the SyncDiscoveredTablesService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.maintenance.workflow_ids import SIGNAL_STOP
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_status import TableStatus
from application.domain.model.managed_table.table_uuid import TableUuid
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.discovery.sync_discovered_tables import (
    SyncDiscoveredTablesUseCase,
    SyncDiscoveredTablesUseCaseInput,
    SyncDiscoveredTablesUseCaseOutput,
)
from application.port.outbound.catalog.read_catalog import ReadCatalogGatewayListInput
from application.port.outbound.workflow.send_table_signal import (
    SendTableSignalGatewayInput,
)
from application.service.discovery.register_discovered_table import (
    register_discovered_table,
)
from application.service.discovery.registration_outcome import RegistrationOutcome
from application.service.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule

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
    from application.port.outbound.workflow.send_table_signal import (
        SendTableSignalGateway,
    )

_REGISTERED = "registered"
_RENAMED = "renamed"
_SKIPPED = "skipped"
_DROP_SCAN_STATUSES = (TableStatus.ACTIVE, TableStatus.PAUSED, TableStatus.EXCLUDED)


class SyncDiscoveredTablesService(SyncDiscoveredTablesUseCase):
    """Make the registry match the tables currently in the catalog."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: ManagedTablesRepo,
        rules_repo: DiscoveryRulesRepo,
        templates_repo: PolicyTemplatesRepo,
        discovery_settings_repo: DiscoverySettingsRepo,
        catalog_gateway: ReadCatalogGateway,
        signal_gateway: SendTableSignalGateway,
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
        self._clock = clock

    def execute(
        self, request: SyncDiscoveredTablesUseCaseInput
    ) -> SyncDiscoveredTablesUseCaseOutput:
        """Register, rename and drop tables within the catalog or namespace scope.

        New tables are registered only while discovery is enabled; renames always run.
        Only a catalog-wide sync (no namespace) marks missing tables dropped, since
        a namespace scan cannot tell a drop from a move. Known tables are never
        re-decided, and a table that fails is counted in ``skipped``.
        """
        now = self._clock()
        enabled = self._discovery_settings_repo.get_settings().enabled
        rules = self._rules_repo.list_all() if enabled else []
        refs = self._catalog_gateway.list_tables(
            ReadCatalogGatewayListInput(request.catalog, request.namespace)
        )
        seen: set[str] = set()
        registered = renamed = skipped = 0
        for ref in refs:
            found = self._catalog_gateway.load_table(ref)
            if found is None:
                continue
            seen.add(found.table_uuid)
            try:
                with translate_domain_errors():
                    outcome = self._sync_table(found, enabled, rules, now)
            except ConflictError, ValidationError, NotFoundError:
                skipped += 1
                continue
            registered += outcome == _REGISTERED
            renamed += outcome == _RENAMED
            skipped += outcome == _SKIPPED
        dropped = 0
        if request.namespace is None:
            with translate_domain_errors():
                dropped = self._drop_missing(request, seen, now)
        return SyncDiscoveredTablesUseCaseOutput(
            registered=registered, renamed=renamed, dropped=dropped, skipped=skipped
        )

    def _sync_table(
        self,
        found: ReadCatalogGatewayTable,
        enabled: bool,
        rules: Sequence[DiscoveryRule],
        now: datetime,
    ) -> str:
        existing = self._tables_repo.get(TableUuid(found.table_uuid))
        if existing is None:
            if not enabled:
                return ""
            outcome = register_discovered_table(
                found,
                rules,
                self._tables_repo,
                self._templates_repo,
                self._signal_gateway,
                now,
            )
            if outcome == RegistrationOutcome.REGISTERED:
                return _REGISTERED
            return _SKIPPED if outcome == RegistrationOutcome.SKIPPED else ""
        name = TableName(found.catalog, found.namespace, found.table)
        if existing.status != TableStatus.DROPPED and existing.name != name:
            existing.rename(name, now)
            self._tables_repo.update(existing)
            return _RENAMED
        return ""

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
            had_workflow = table.needs_reconcile_workflow
            table.mark_dropped(now)
            self._tables_repo.update(table)
            dropped += 1
            if had_workflow:
                self._signal_gateway.send(
                    SendTableSignalGatewayInput(
                        table_uuid=table.id.value, signal=SIGNAL_STOP
                    )
                )
        return dropped


def _in_scope(name: TableName, request: SyncDiscoveredTablesUseCaseInput) -> bool:
    if name.catalog != request.catalog:
        return False
    return request.namespace is None or name.namespace == request.namespace
