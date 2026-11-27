"""Test the policy placements store, the SQL one and the in-memory fake alike, over all three holders."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.catalog.sql import CatalogsSqlRepo
from context.table_maintenance.adapter.outbound.namespace.sql import NamespacesSqlRepo
from context.table_maintenance.adapter.outbound.shared.sql import PolicyPlacementsSqlStore
from context.table_maintenance.adapter.outbound.table.sql import TablesSqlRepo
from context.table_maintenance.application.domain.model.catalog import Catalog
from context.table_maintenance.application.domain.model.namespace import Namespace
from context.table_maintenance.application.domain.model.shared import (
    CatalogId,
    NamespaceId,
    PolicyPlacement,
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryPolicyId,
    TableId,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table import Table, TableName
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo
from tests.context.table_maintenance.fakes.in_memory_policy_placements_store import InMemoryPolicyPlacementsStore
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo
    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo
    from context.table_maintenance.application.port.outbound.shared import PolicyPlacementsStore
    from context.table_maintenance.application.port.outbound.table import TablesRepo

NOW = datetime(2026, 11, 27, tzinfo=UTC)
SALES = TableDiscoveryPolicyId("dp-00000000000000000000000001")
OTHER = TableDiscoveryPolicyId("dp-00000000000000000000000002")
NIGHTLY = TableMaintenancePolicyId("mp-00000000000000000000000001")


@dataclass
class _Holders:
    """The three repos a placement is read from, and the store that reads them."""

    catalogs: CatalogsRepo
    namespaces: NamespacesRepo
    tables: TablesRepo
    store: PolicyPlacementsStore

    def catalog(self, name: str, *, discovery=None, maintenance=None) -> None:
        catalog = Catalog.register(CatalogId(name), NOW)
        if discovery is not None:
            catalog.attach_discovery_policy(discovery, NOW)
        if maintenance is not None:
            catalog.attach_maintenance_policy(maintenance, NOW)
        self.catalogs.create(catalog)

    def namespace(self, catalog: str, levels: tuple[str, ...], *, discovery=None, maintenance=None) -> None:
        namespace = Namespace.register(NamespaceId.of(catalog, levels), NOW)
        if discovery is not None:
            namespace.attach_discovery_policy(discovery, NOW)
        if maintenance is not None:
            namespace.attach_maintenance_policy(maintenance, NOW)
        self.namespaces.create(namespace)

    def table(self, uuid: str, name: TableName, *, discovery=None, maintenance=None) -> Table:
        table = Table.register_undecided(TableId(uuid), name, NOW)
        if discovery is not None:
            table.attach_discovery_policy(discovery, NOW)
        if maintenance is not None:
            table.attach_maintenance_policy(maintenance, NOW)
        self.tables.create(table)
        return table


@pytest.fixture(params=["sql", "memory"])
def holders(request: pytest.FixtureRequest, engine: Engine) -> _Holders:
    """Provide each store implementation over the repos it reads."""
    if request.param == "sql":
        return _Holders(
            CatalogsSqlRepo(engine), NamespacesSqlRepo(engine), TablesSqlRepo(engine), PolicyPlacementsSqlStore(engine)
        )
    catalogs, namespaces, tables = InMemoryCatalogsRepo(), InMemoryNamespacesRepo(), InMemoryTablesRepo()
    return _Holders(catalogs, namespaces, tables, InMemoryPolicyPlacementsStore(catalogs, namespaces, tables))


def _placement(type_: PolicyTargetType, *path: str, table_uuid: str | None = None) -> PolicyPlacement:
    return PolicyPlacement(target=PolicyTarget(type=type_, path=path, table_uuid=table_uuid))


ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders")


def test_discovery_placements_name_every_holder_of_the_policy(holders: _Holders):
    """A policy on a catalog, a namespace and a table is placed three times, by type and then path."""
    holders.table("u1", ORDERS, discovery=SALES)
    holders.namespace("iceberg", ("sales", "eu"), discovery=SALES)
    holders.catalog("iceberg", discovery=SALES)
    holders.catalog("other", discovery=OTHER)

    assert holders.store.discovery_placements(SALES) == (
        _placement(PolicyTargetType.CATALOG, "iceberg"),
        _placement(PolicyTargetType.NAMESPACE, "iceberg", "sales", "eu"),
        _placement(PolicyTargetType.TABLE, "iceberg", "sales", "eu", "orders", table_uuid="u1"),
    )


def test_a_policy_attached_nowhere_has_no_placement(holders: _Holders):
    """A place holding another policy, or none, does not place this one."""
    holders.catalog("iceberg", discovery=OTHER)
    holders.namespace("iceberg", ("sales",))

    assert holders.store.discovery_placements(SALES) == ()


def test_maintenance_placements_read_the_maintenance_column(holders: _Holders):
    """A maintenance policy is placed where it is held; a discovery policy on the same place does not count."""
    holders.catalog("iceberg", discovery=SALES, maintenance=NIGHTLY)
    holders.namespace("iceberg", ("sales",), discovery=SALES)
    holders.table("u1", ORDERS, maintenance=NIGHTLY)

    assert holders.store.maintenance_placements(NIGHTLY) == (
        _placement(PolicyTargetType.CATALOG, "iceberg"),
        _placement(PolicyTargetType.TABLE, "iceberg", "sales", "eu", "orders", table_uuid="u1"),
    )


def test_a_dropped_tables_placement_is_gone(holders: _Holders):
    """Dropping a table lets go of its policies, so it places none and its catalog no longer counts."""
    table = holders.table("u1", ORDERS, discovery=SALES, maintenance=NIGHTLY)
    table.mark_dropped(NOW)
    holders.tables.update(table)

    assert holders.store.discovery_placements(SALES) == ()
    assert holders.store.maintenance_placements(NIGHTLY) == ()
    assert holders.store.catalogs_with_discovery_policy() == frozenset()


def test_catalogs_with_a_discovery_policy_count_every_holder(holders: _Holders):
    """A catalog counts when it, a namespace or a table of it holds a discovery policy; maintenance does not."""
    holders.catalog("by_catalog", discovery=SALES)
    holders.namespace("by_namespace", ("sales",), discovery=OTHER)
    holders.table("u1", TableName(catalog="by_table", namespace="ns", table="t"), discovery=SALES)
    holders.catalog("maintenance_only", maintenance=NIGHTLY)
    holders.catalog("empty")

    assert holders.store.catalogs_with_discovery_policy() == frozenset({"by_catalog", "by_namespace", "by_table"})
