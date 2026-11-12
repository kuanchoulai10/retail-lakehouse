"""Define the SyncDiscoveredTablesService."""

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
from context.table_maintenance.application.service.table.apply_discovery_to_known_table import (
    apply_discovery_to_known_table,
)
from context.table_maintenance.application.service.table.register_discovered_table import (
    register_discovered_table,
)
from context.table_maintenance.application.service.table.registration_outcome import (
    RegistrationOutcome,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.domain.model.table_discovery_rules import (
        TableDiscoveryRules,
    )
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendTableChangeGateway,
        TableMetadata,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_rules import (
        TableDiscoveryRulesRepo,
    )
    from context.table_maintenance.application.service.table.known_table_outcome import (
        KnownTableOutcome,
    )

_DROP_SCAN_STATUSES = (TableStatus.MANAGED, TableStatus.UNMANAGED)


class SyncDiscoveredTablesService(SyncDiscoveredTablesUseCase):
    """Make the registry match the tables currently in the catalog and the discovery rules."""

    def __init__(
        self,
        tables_repo: TablesRepo,
        rules_repo: TableDiscoveryRulesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        table_change_gateway: SendTableChangeGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._rules_repo = rules_repo
        self._catalog_gateway = catalog_gateway
        self._table_change_gateway = table_change_gateway
        self._clock = clock

    def execute(self, request: SyncDiscoveredTablesUseCaseInput) -> SyncDiscoveredTablesUseCaseOutput:
        """Register, rename, decide and drop tables within the catalog or namespace scope.

        Every table listed is decided by the discovery rules: an unknown one is
        registered, as managed when the rules include it and unmanaged otherwise, a known one is managed or unmanaged
        as the rules now say (counted in ``managed`` / ``unmanaged``); with no
        rules nothing is managed. Only a catalog-wide sync (no namespace) marks missing tables
        dropped, since a namespace scan cannot tell a drop from a move, and a
        table it does not list is never decided. A table that fails is counted in
        ``skipped``. A catalog-wide sync also signal-with-starts the
        reconciliation workflow of every known managed table (counted in
        ``ensured``), so a table whose workflow was never started, or was lost,
        is picked up again.
        """
        now = self._clock()
        rules = self._rules_repo.get_rules()
        seen_change = TableChange.SEEN if request.namespace is None else None
        refs = self._catalog_gateway.list_tables(ReadTableMetadataGatewayListInput(request.catalog, request.namespace))
        seen: set[str] = set()
        known: list[KnownTableOutcome] = []
        registered = skipped = 0
        for ref in refs:
            found = self._catalog_gateway.load_table(ref)
            if found is None:
                continue
            seen.add(found.table_uuid)
            try:
                with translate_domain_errors():
                    outcome = self._sync_table(found, rules, seen_change, now)
            except ConflictError, ValidationError, NotFoundError:
                skipped += 1
                continue
            if isinstance(outcome, RegistrationOutcome):
                registered += 1
            elif outcome is not None:
                known.append(outcome)
        dropped = 0
        if request.namespace is None:
            with translate_domain_errors():
                dropped = self._drop_missing(request, seen, now)
        return SyncDiscoveredTablesUseCaseOutput(
            registered=registered,
            renamed=sum(o.renamed for o in known),
            dropped=dropped,
            skipped=skipped,
            ensured=sum(o.signalled for o in known),
            managed=sum(o.change == TableManagementChange.MANAGED for o in known),
            unmanaged=sum(o.change == TableManagementChange.UNMANAGED for o in known),
        )

    def _sync_table(
        self,
        found: TableMetadata,
        rules: TableDiscoveryRules,
        seen_change: TableChange | None,
        now: datetime,
    ) -> RegistrationOutcome | KnownTableOutcome | None:
        """Register an unknown table, or apply the discovery to a known live one; None for neither."""
        existing = self._tables_repo.get(TableId(found.table_uuid))
        if existing is None:
            return register_discovered_table(
                found, rules, self._tables_repo, self._table_change_gateway, TableChange.SEEN, now
            )
        if existing.status == TableStatus.DROPPED:
            return None
        name = TableName(catalog=found.catalog, namespace=found.namespace, table=found.table)
        return apply_discovery_to_known_table(
            existing, name, rules, self._tables_repo, self._table_change_gateway, seen_change, now
        )

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
            was_managed = table.is_managed
            table.mark_dropped(now)
            self._tables_repo.update(table)
            dropped += 1
            if was_managed:
                self._table_change_gateway.send(
                    SendTableChangeGatewayInput(
                        table_uuid=table.id.value,
                        table_name=table.name.fully_qualified(),
                        change=TableChange.STOPPED.value,
                        is_managed=table.is_managed,
                    )
                )
        return dropped


def _in_scope(name: TableName, request: SyncDiscoveredTablesUseCaseInput) -> bool:
    if name.catalog != request.catalog:
        return False
    return request.namespace is None or name.namespace == request.namespace
