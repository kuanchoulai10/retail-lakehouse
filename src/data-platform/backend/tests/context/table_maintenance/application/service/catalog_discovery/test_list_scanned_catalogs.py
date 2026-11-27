"""Test ListScannedCatalogsService: the catalogs discovery scans, with their scan state."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.catalog_discovery import CatalogDiscovery
from context.table_maintenance.application.domain.model.namespace import Namespace
from context.table_maintenance.application.domain.model.shared import NamespaceId, TableId
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.port.inbound.catalog_discovery import ListScannedCatalogsUseCaseInput
from context.table_maintenance.application.service.catalog_discovery import ListScannedCatalogsService
from tests.context.table_maintenance.application.domain.service.table_discovery_policy.discovery_policy_samples import (  # noqa: E501
    MANAGE_ALL,
    UNMANAGE_ALL,
)
from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import InMemoryCatalogDiscoveriesRepo
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo
from tests.context.table_maintenance.fakes.in_memory_policy_placements_store import InMemoryPolicyPlacementsStore
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def test_the_scanned_catalogs_are_those_holding_a_policy_and_those_holding_managed_tables() -> None:
    """A catalog is scanned while a discovery policy is attached in it or it still holds a managed table, by name."""
    tables, namespaces, discoveries = InMemoryTablesRepo(), InMemoryNamespacesRepo(), InMemoryCatalogDiscoveriesRepo()
    placements = InMemoryPolicyPlacementsStore(InMemoryCatalogsRepo(), namespaces, tables)
    namespace = Namespace.register(NamespaceId.of("zeta", ("sales",)), NOW)
    namespace.attach_discovery_policy(UNMANAGE_ALL.id, NOW)
    namespaces.create(namespace)
    held = TableName(catalog="beta", namespace="hr", table="people")
    tables.create(Table.register(TableId("u-1"), held, MANAGE_ALL.should_manage(held), NOW))
    unmanaged = TableName(catalog="gamma", namespace="hr", table="people")
    tables.create(Table.register(TableId("u-2"), unmanaged, UNMANAGE_ALL.should_manage(unmanaged), NOW))
    discoveries.save(CatalogDiscovery.first("beta", NOW))
    discoveries.save(CatalogDiscovery.first("gamma", NOW))

    out = ListScannedCatalogsService(placements, tables, discoveries).execute(ListScannedCatalogsUseCaseInput())

    assert [(c.catalog, c.last_discovered_at) for c in out.catalogs] == [("beta", NOW), ("zeta", None)]
