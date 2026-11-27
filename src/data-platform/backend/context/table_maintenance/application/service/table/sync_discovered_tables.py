"""Define the SyncDiscoveredTablesService."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogDiscovery,
    CatalogScanFailure,
    CatalogScanFailureReason,
)
from context.table_maintenance.application.domain.model.shared import CatalogDiscoveryId, TableId
from context.table_maintenance.application.domain.model.table import (
    TableChange,
    TableManagementChange,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.exceptions import (
    ConcurrentUpdateError,
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
    CatalogAccessDeniedError,
    CatalogNotFoundError,
    ReadTableMetadataGatewayListInput,
    SendTableChangeGatewayInput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors
from context.table_maintenance.application.service.table.apply_discovery_to_known_table import (
    apply_discovery_to_known_table,
)
from context.table_maintenance.application.service.table.discovery_decider import DiscoveryDecider
from context.table_maintenance.application.service.table.last_commit_of import last_commit_of
from context.table_maintenance.application.service.table.register_discovered_table import (
    register_discovered_table,
)
from context.table_maintenance.application.service.table.registration_outcome import (
    RegistrationOutcome,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.catalog_discovery import (
        CatalogDiscoveriesRepo,
    )
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import (
        ReadTableMetadataGateway,
        SendTableChangeGateway,
        TableMetadata,
        TablesRepo,
    )
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )
    from context.table_maintenance.application.service.table.known_table_outcome import (
        KnownTableOutcome,
    )

logger = logging.getLogger(__name__)

_DROP_SCAN_STATUSES = (TableStatus.MANAGED, TableStatus.UNMANAGED, TableStatus.UNDECIDED)
_RETIRED_STATUSES = (TableStatus.MANAGED, TableStatus.UNDECIDED)


class SyncDiscoveredTablesService(SyncDiscoveredTablesUseCase):
    """Make the registry match the tables currently in the catalog and their nearest discovery policies."""

    def __init__(  # noqa: PLR0913
        self,
        tables_repo: TablesRepo,
        discovery_policies_repo: TableDiscoveryPoliciesRepo,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        placements: PolicyPlacementsStore,
        discoveries_repo: CatalogDiscoveriesRepo,
        catalog_gateway: ReadTableMetadataGateway,
        table_change_gateway: SendTableChangeGateway,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, the placements, the gateways and the clock."""
        self._tables_repo = tables_repo
        self._discovery_policies_repo = discovery_policies_repo
        self._catalogs_repo = catalogs_repo
        self._namespaces_repo = namespaces_repo
        self._placements = placements
        self._discoveries_repo = discoveries_repo
        self._catalog_gateway = catalog_gateway
        self._table_change_gateway = table_change_gateway
        self._clock = clock

    def execute(self, request: SyncDiscoveredTablesUseCaseInput) -> SyncDiscoveredTablesUseCaseOutput:
        """Register, rename, decide and drop tables within the catalog or namespace scope.

        Every table listed is decided by its nearest discovery policy (docs/adr/0012): the one
        it holds itself, else its namespaces' and its catalog's, read once for the whole scan. An
        unknown one is registered, as managed or unmanaged as the decision says, a known one
        (an undecided one included) is managed or unmanaged as it now says (counted in
        ``managed`` / ``unmanaged``; an undecided table that ends up unmanaged is saved and counted
        in neither), and each records the policy, version and rule position that decided it;
        with no policy on its walk it is not managed and nothing decided it. Only a
        catalog-wide sync (no namespace) marks missing tables dropped, since a namespace scan
        cannot tell a drop from a move, and a table it does not list is never decided. A table that fails is counted in
        ``skipped``, a table another writer saved while the scan decided or dropped it included (logged and left as
        that writer stored it; the next scan decides it). A catalog-wide sync also signal-with-starts the
        reconciliation workflow of every known managed table (counted in
        ``ensured``), so a table whose workflow was never started, or was lost,
        is picked up again. A table that ends up newly managed (registered or
        managed again) is sent ``managed``, which checks it at once; the ``seen``
        sent to a table already managed only keeps its workflow and checks nothing.

        Every table read from the catalog has its last commit moved to its newest
        commit. A catalog-wide sync that completes records the catalog's
        discovery at the time it started, which stands for the last time each live
        table was discovered, so a table is saved only when something about it
        changed; a table it drops keeps the catalog's previous discovery as the
        last time it was seen.

        A scan whose catalog refuses the credential (CatalogAccessDeniedError) or no
        longer exists (CatalogNotFoundError) records a ``CatalogScanFailure`` on the
        catalog's discovery at the time it started, changes no table it would have to read and
        returns with ``failure`` set: retrying a refusal changes nothing. Any other error still fails
        the scan. A single table the credential cannot load is counted in ``skipped``,
        and that scan drops no table, since a table that cannot be read must never read
        as dropped.

        A catalog-wide scan of a catalog where no table can end up managed (no policy is attached in it,
        or every attached policy only excludes) also decides, from its stored row, each managed or
        undecided table it could not read: all of them when the catalog cannot be read, the ones it
        could not load otherwise (the drop pass handles the rest). A managed one is unmanaged.
        Each is sent ``stopped`` and records what decided it (the excluding policy, or nothing). Every
        table there is not managed, so no catalog read is needed, and no table is left managed under no
        policy that could include it.
        """
        now = self._clock()
        decider = DiscoveryDecider.for_catalog(
            request.catalog,
            self._catalogs_repo,
            self._namespaces_repo,
            self._discovery_policies_repo,
            self._placements,
            self._tables_repo,
        )
        seen_change = TableChange.SEEN if request.namespace is None else None
        retires = request.namespace is None and not decider.can_include_any()
        try:
            refs = self._catalog_gateway.list_tables(
                ReadTableMetadataGatewayListInput(request.catalog, request.namespace)
            )
        except (CatalogAccessDeniedError, CatalogNotFoundError) as exc:
            retired_unmanaged, retired_skipped = (
                self._unmanage_stored(request.catalog, decider, now, seen=set()) if retires else (0, 0)
            )
            reason = self._record_failure(request.catalog, exc, now)
            return SyncDiscoveredTablesUseCaseOutput(
                registered=0,
                renamed=0,
                dropped=0,
                skipped=retired_skipped,
                unmanaged=retired_unmanaged,
                failure=reason.value,
            )
        seen: set[str] = set()
        known: list[KnownTableOutcome] = []
        registered = skipped = retired_unmanaged = 0
        read_every_table = True
        for ref in refs:
            try:
                found = self._catalog_gateway.load_table(ref)
            except CatalogAccessDeniedError:
                skipped += 1
                read_every_table = False
                continue
            if found is None:
                continue
            seen.add(found.table_uuid)
            try:
                with translate_domain_errors():
                    outcome = self._sync_table(found, decider, seen_change, now)
            except ConcurrentUpdateError as exc:
                _log_changed_meanwhile(exc)
                skipped += 1
                continue
            except ConflictError, ValidationError, NotFoundError:
                skipped += 1
                continue
            if isinstance(outcome, RegistrationOutcome):
                registered += 1
            elif outcome is not None:
                known.append(outcome)
        dropped = 0
        if request.namespace is None:
            if retires and not read_every_table:
                retired_unmanaged, retired_skipped = self._unmanage_stored(request.catalog, decider, now, seen=seen)
                skipped += retired_skipped
            with translate_domain_errors():
                if read_every_table:
                    dropped, drop_skipped = self._drop_missing(request, seen, now)
                    skipped += drop_skipped
                self._record_discovery(request.catalog, now)
        return SyncDiscoveredTablesUseCaseOutput(
            registered=registered,
            renamed=sum(o.renamed for o in known),
            dropped=dropped,
            skipped=skipped,
            ensured=sum(o.notified for o in known),
            managed=sum(o.change == TableManagementChange.MANAGED for o in known),
            unmanaged=retired_unmanaged + sum(o.change == TableManagementChange.UNMANAGED for o in known),
        )

    def _sync_table(
        self,
        found: TableMetadata,
        decider: DiscoveryDecider,
        seen_change: TableChange | None,
        now: datetime,
    ) -> RegistrationOutcome | KnownTableOutcome | None:
        """Register an unknown table, or apply the discovery to a known live one; None for neither."""
        existing = self._tables_repo.get(TableId(found.table_uuid))
        if existing is not None and existing.status == TableStatus.DROPPED:
            return None
        name = TableName(catalog=found.catalog, namespace=found.namespace, table=found.table)
        decision = decider.decide(name, existing)
        if existing is None:
            return register_discovered_table(found, decision, self._tables_repo, self._table_change_gateway, now)
        return apply_discovery_to_known_table(
            existing,
            name,
            decision,
            self._tables_repo,
            self._table_change_gateway,
            seen_change,
            now,
            last_committed_at=last_commit_of(found),
        )

    def _unmanage_stored(
        self, catalog: str, decider: DiscoveryDecider, now: datetime, *, seen: set[str]
    ) -> tuple[int, int]:
        """Decide the catalog's stored managed and undecided tables not in ``seen``; return (unmanaged, skipped).

        Only for a catalog where no attached policy can include, so every table is not managed: no
        catalog read is needed, so even a catalog the credential cannot read, or that is gone, has its
        managed tables unmanaged and each sent ``stopped``, and its undecided tables unmanaged and saved.
        Each is decided by its stored name. A table the scan read was decided already.
        """
        unmanaged = skipped = 0
        for table in self._tables_repo.list_by_statuses(_RETIRED_STATUSES):
            if table.name.catalog != catalog or table.id.value in seen:
                continue
            try:
                with translate_domain_errors():
                    outcome = apply_discovery_to_known_table(
                        table,
                        table.name,
                        decider.decide(table.name, table),
                        self._tables_repo,
                        self._table_change_gateway,
                        None,
                        now,
                    )
            except ConcurrentUpdateError as exc:
                _log_changed_meanwhile(exc)
                skipped += 1
                continue
            except ConflictError, ValidationError, NotFoundError:
                skipped += 1
                continue
            unmanaged += outcome.change == TableManagementChange.UNMANAGED
        return unmanaged, skipped

    def _record_failure(
        self, catalog: str, error: CatalogAccessDeniedError | CatalogNotFoundError, now: datetime
    ) -> CatalogScanFailureReason:
        reason = (
            CatalogScanFailureReason.CANNOT_ACCESS
            if isinstance(error, CatalogAccessDeniedError)
            else CatalogScanFailureReason.NOT_FOUND
        )
        failure = CatalogScanFailure(reason=reason, detail=str(error), failed_at=now)
        discovery = self._discoveries_repo.get(CatalogDiscoveryId(catalog))
        if discovery is None:
            discovery = CatalogDiscovery.failed(catalog, failure)
        else:
            discovery.record_failure(failure)
        self._discoveries_repo.save(discovery)
        return reason

    def _record_discovery(self, catalog: str, now: datetime) -> None:
        discovery = self._discoveries_repo.get(CatalogDiscoveryId(catalog))
        if discovery is None:
            discovery = CatalogDiscovery.first(catalog, now)
        else:
            discovery.record(now)
        self._discoveries_repo.save(discovery)

    def _drop_missing(
        self,
        request: SyncDiscoveredTablesUseCaseInput,
        seen: set[str],
        now: datetime,
    ) -> tuple[int, int]:
        """Mark dropped each stored live table of the scope the scan did not see; return (dropped, skipped).

        A table another writer saved since it was listed is skipped and left as stored: the next scan drops it.
        """
        dropped = skipped = 0
        previous = self._discoveries_repo.get(CatalogDiscoveryId(request.catalog))
        last_seen = None if previous is None else previous.last_discovered_at
        for table in self._tables_repo.list_by_statuses(_DROP_SCAN_STATUSES):
            if table.id.value in seen or not _in_scope(table.name, request):
                continue
            was_managed = table.is_managed
            table.mark_dropped(now, catalog_discovered_at=last_seen)
            try:
                self._tables_repo.update(table)
            except ConcurrentUpdateError as exc:
                _log_changed_meanwhile(exc)
                skipped += 1
                continue
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
        return dropped, skipped


def _log_changed_meanwhile(error: ConcurrentUpdateError) -> None:
    logger.warning("skipping a table the scan could not save: %s; the next scan decides it", error)


def _in_scope(name: TableName, request: SyncDiscoveredTablesUseCaseInput) -> bool:
    if name.catalog != request.catalog:
        return False
    return request.namespace is None or name.namespace == request.namespace
