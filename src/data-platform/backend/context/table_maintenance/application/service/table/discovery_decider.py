"""Define the DiscoveryDecider."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import CatalogId, NamespaceId
from context.table_maintenance.application.domain.model.table import TableStatus
from context.table_maintenance.application.domain.service.shared import nearest_discovery_policy
from context.table_maintenance.application.domain.service.table_discovery_policy import decide_table_discovery

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from context.table_maintenance.application.domain.model.catalog import Catalog
    from context.table_maintenance.application.domain.model.namespace import Namespace
    from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
    from context.table_maintenance.application.domain.model.table import Table, TableName
    from context.table_maintenance.application.domain.model.table_discovery_policy import (
        ManagementDecision,
        TableDiscoveryPolicy,
    )
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import TablesRepo
    from context.table_maintenance.application.port.outbound.table_discovery_policy import (
        TableDiscoveryPoliciesRepo,
    )

_LIVE = (TableStatus.MANAGED, TableStatus.UNMANAGED, TableStatus.UNDECIDED)


class DiscoveryDecider:
    """Decide discovered tables by their nearest discovery policy, from the places read once.

    A scan reads its catalog's record and all its namespaces once (``for_catalog``) and decides every
    table it lists from them, together with the policy the table itself holds; a catalog event reads
    only the catalog and the namespaces enclosing its one table (``for_table``). Either way the
    decision is ``decide_table_discovery``'s over ``nearest_discovery_policy``, so a table with no
    policy on its walk is not managed, and nothing decided it. Each policy is read once, when first
    needed.
    """

    def __init__(  # noqa: PLR0913
        self,
        catalog_name: str,
        catalog: Catalog | None,
        namespaces: Sequence[Namespace],
        policies_repo: TableDiscoveryPoliciesRepo,
        *,
        catalog_has_policy: bool | None = None,
        tables_repo: TablesRepo | None = None,
    ) -> None:
        """Hold the places read of ``catalog_name`` and read the policies they hold.

        ``catalog_has_policy`` says whether a discovery policy is attached anywhere in the catalog (a
        table included), and ``tables_repo`` reads the catalog's tables; a scan gives both.
        """
        self._catalog_name = catalog_name
        self._catalog = catalog
        self._namespaces = tuple(namespaces)
        self._policies_repo = policies_repo
        self._catalog_has_policy = catalog_has_policy
        self._tables_repo = tables_repo
        self._policies: dict[TableDiscoveryPolicyId, TableDiscoveryPolicy] = {}
        self._read(place.discovery_policy_id for place in self._places())

    @classmethod
    def for_catalog(  # noqa: PLR0913
        cls,
        catalog: str,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        policies_repo: TableDiscoveryPoliciesRepo,
        placements: PolicyPlacementsStore,
        tables_repo: TablesRepo,
    ) -> DiscoveryDecider:
        """Read the catalog's record, its namespaces and their policies, to decide any table in it."""
        return cls(
            catalog,
            catalogs_repo.get(CatalogId(catalog)),
            namespaces_repo.list_in_catalog(catalog),
            policies_repo,
            catalog_has_policy=catalog in placements.catalogs_with_discovery_policy(),
            tables_repo=tables_repo,
        )

    @classmethod
    def for_table(
        cls,
        name: TableName,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        policies_repo: TableDiscoveryPoliciesRepo,
    ) -> DiscoveryDecider:
        """Read the catalog and the namespaces enclosing one table, and their policies, to decide that table."""
        enclosing = NamespaceId.enclosing(name.catalog, name.namespace)
        catalog = catalogs_repo.get(CatalogId(name.catalog))
        return cls(name.catalog, catalog, namespaces_repo.get_many(enclosing), policies_repo)

    def decide(self, name: TableName, table: Table | None) -> ManagementDecision:
        """Decide the table by its current name and the policy it holds itself (``table`` None for a new one)."""
        nearest = nearest_discovery_policy(table, self._namespaces, self._catalog, name=name)
        if nearest is not None:
            self._read((nearest.policy_id,))
        return decide_table_discovery(name, nearest, self._policies)

    def has_any_policy(self) -> bool:
        """Return whether a discovery policy is attached anywhere in the catalog: to it, a namespace or a table.

        Read ``for_catalog``; the table part is the placements' answer, so no table is read for it.
        """
        if self._catalog_has_policy is not None:
            return self._catalog_has_policy
        return any(place.discovery_policy_id is not None for place in self._places())

    def can_include_any(self) -> bool:
        """Return whether a discovery policy attached in the catalog could include some table.

        Read ``for_catalog``, this says whether a table in the catalog could end up managed. When it
        cannot (no policy is attached anywhere in it, or every attached policy only excludes), every
        table there is not managed, so a catalog-wide scan unmanages the stored tables without reading
        the catalog. The catalog's tables are read only when its record and namespaces hold no policy
        that includes.
        """
        if not self.has_any_policy():
            return False
        if self._any_includes(place.discovery_policy_id for place in self._places()):
            return True
        return self._any_includes(table.discovery_policy_id for table in self._catalog_tables())

    def _any_includes(self, policy_ids: Iterable[TableDiscoveryPolicyId | None]) -> bool:
        held = [policy_id for policy_id in policy_ids if policy_id is not None]
        self._read(held)
        return any(policy_id in self._policies and self._policies[policy_id].can_include() for policy_id in held)

    def _catalog_tables(self) -> list[Table]:
        if self._tables_repo is None:
            return []
        return [t for t in self._tables_repo.list_by_statuses(_LIVE) if t.name.catalog == self._catalog_name]

    def _places(self) -> tuple[Catalog | Namespace, ...]:
        return (*self._namespaces, *(() if self._catalog is None else (self._catalog,)))

    def _read(self, policy_ids: Iterable[TableDiscoveryPolicyId | None]) -> None:
        missing = list(dict.fromkeys(p for p in policy_ids if p is not None and p not in self._policies))
        if missing:
            read = {policy.id: policy for policy in self._policies_repo.get_many(missing)}
            self._policies = {**self._policies, **read}
