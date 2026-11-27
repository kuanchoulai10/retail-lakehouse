"""Define the PolicyHolders read of one place."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import CatalogId, NamespaceId, TableId
from context.table_maintenance.application.domain.model.table import TableName
from context.table_maintenance.application.domain.service.shared import (
    nearest_discovery_policy,
    nearest_maintenance_policy,
)
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.outbound.table import CatalogNotFoundError, TableMetadataRef
from context.table_maintenance.application.service.shared.translate_domain_errors import translate_domain_errors

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.table_maintenance.application.domain.model.catalog import Catalog
    from context.table_maintenance.application.domain.model.namespace import Namespace
    from context.table_maintenance.application.domain.model.shared import (
        TableDiscoveryPolicyId,
        TableMaintenancePolicyId,
    )
    from context.table_maintenance.application.domain.model.table import Table
    from context.table_maintenance.application.domain.service.shared import NearestPolicy
    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo


class PolicyHolders:
    """The records that may hold a policy for one place: its table, the namespaces enclosing it, its catalog.

    Every kind of policy walks the same holders nearest first, so each kind finds its own nearest
    policy: the table by its uuid (one table maintenance does not record holds nothing), then the
    namespaces deepest first, then the catalog. ``name`` is where a table is now, so a renamed or
    moved table is walked under its current namespaces.
    """

    def __init__(
        self,
        table: Table | None,
        namespaces: Sequence[Namespace],
        catalog: Catalog | None,
        name: TableName | None,
    ) -> None:
        """Hold the holders read for the place and the table's current name, None for a catalog or namespace."""
        self.table = table
        self.namespaces = tuple(namespaces)
        self.catalog = catalog
        self.name = name

    @classmethod
    def of_place(  # noqa: PLR0913
        cls,
        gateway: ReadTableMetadataGateway,
        tables_repo: TablesRepo,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        *,
        catalog: str | None,
        namespace: str | None,
        table: str | None,
        table_uuid: str | None,
    ) -> PolicyHolders:
        """Read the holders of the place a request names.

        A ``table_uuid`` without ``catalog`` names a table table maintenance records, placed by its
        recorded name (NotFoundError without a record; ValidationError with neither). A catalog, or a
        catalog and a dot-joined namespace, walks from that level up without reading the catalog:
        whether the place exists is the caller's question. A table by name takes the ``table_uuid``
        given, else its uuid from the catalog (NotFoundError when the catalog does not hold it; a
        refused catalog raises CatalogAccessDeniedError, untouched).
        """
        if catalog is None:
            return cls._of_recorded_table(tables_repo, catalogs_repo, namespaces_repo, table_uuid)
        if table is None:
            return cls._read(catalogs_repo, namespaces_repo, None, catalog, namespace or "", None)
        if namespace is None:
            raise ValidationError("a table needs its namespace")
        if table_uuid is None:
            table_uuid = _uuid_in_catalog(gateway, catalog, namespace, table)
        with translate_domain_errors():
            name = TableName(catalog=catalog, namespace=namespace, table=table)
        return cls._read(catalogs_repo, namespaces_repo, tables_repo.get(TableId(table_uuid)), catalog, namespace, name)

    def nearest_maintenance_policy(self) -> NearestPolicy[TableMaintenancePolicyId] | None:
        """Return the nearest maintenance policy and where it is attached; None leaves the platform default."""
        return nearest_maintenance_policy(self.table, self.namespaces, self.catalog, name=self.name)

    def nearest_discovery_policy(self) -> NearestPolicy[TableDiscoveryPolicyId] | None:
        """Return the nearest discovery policy and where it is attached; None when no discovery policy applies."""
        return nearest_discovery_policy(self.table, self.namespaces, self.catalog, name=self.name)

    @classmethod
    def _of_recorded_table(
        cls,
        tables_repo: TablesRepo,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        table_uuid: str | None,
    ) -> PolicyHolders:
        if table_uuid is None:
            raise ValidationError("name a catalog or a table uuid")
        recorded = tables_repo.get(TableId(table_uuid))
        if recorded is None:
            raise NotFoundError(f"table {table_uuid} not found")
        name = recorded.name
        return cls._read(catalogs_repo, namespaces_repo, recorded, name.catalog, name.namespace, name)

    @classmethod
    def _read(  # noqa: PLR0913
        cls,
        catalogs_repo: CatalogsRepo,
        namespaces_repo: NamespacesRepo,
        table: Table | None,
        catalog: str,
        namespace: str,
        name: TableName | None,
    ) -> PolicyHolders:
        """Read the namespaces enclosing ``namespace`` in one read, and the catalog."""
        with translate_domain_errors():
            enclosing = NamespaceId.enclosing(catalog, namespace)
            catalog_id = CatalogId(catalog)
        namespaces = namespaces_repo.get_many(enclosing) if enclosing else []
        return cls(table, namespaces, catalogs_repo.get(catalog_id), name)


def _uuid_in_catalog(gateway: ReadTableMetadataGateway, catalog: str, namespace: str, table: str) -> str:
    try:
        loaded = gateway.load_table(TableMetadataRef(catalog=catalog, namespace=namespace, table=table))
    except CatalogNotFoundError as exc:
        raise NotFoundError(str(exc)) from exc
    if loaded is None:
        raise NotFoundError(f"table {catalog}.{namespace}.{table} not found")
    return loaded.table_uuid
