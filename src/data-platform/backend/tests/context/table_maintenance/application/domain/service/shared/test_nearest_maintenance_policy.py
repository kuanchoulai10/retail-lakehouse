"""Test nearest_maintenance_policy: the same walk as discovery, over the maintenance policies held."""

from __future__ import annotations

from datetime import UTC, datetime

from context.table_maintenance.application.domain.model.catalog import Catalog
from context.table_maintenance.application.domain.model.namespace import Namespace
from context.table_maintenance.application.domain.model.shared import (
    CatalogId,
    NamespaceId,
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryPolicyId,
    TableId,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.domain.service.shared import NearestPolicy, nearest_maintenance_policy

NOW = datetime(2026, 11, 1, tzinfo=UTC)
ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders")
ON_TABLE = TableMaintenancePolicyId.new()
ON_SALES = TableMaintenancePolicyId.new()
ON_CATALOG = TableMaintenancePolicyId.new()


def _table(policy: TableMaintenancePolicyId | None = None) -> Table:
    table = Table.register_undecided(TableId("u1"), ORDERS, NOW)
    if policy is not None:
        table.attach_maintenance_policy(policy, NOW)
    return table


def _sales(policy: TableMaintenancePolicyId | None) -> Namespace:
    namespace = Namespace.register(NamespaceId.of("iceberg", ("sales",)), NOW)
    if policy is not None:
        namespace.attach_maintenance_policy(policy, NOW)
    return namespace


def _catalog(policy: TableMaintenancePolicyId | None) -> Catalog:
    catalog = Catalog.register(CatalogId("iceberg"), NOW)
    if policy is not None:
        catalog.attach_maintenance_policy(policy, NOW)
    return catalog


def test_the_tables_own_maintenance_policy_beats_its_namespace():
    """A maintenance policy on the table itself is nearer than its namespace's."""
    nearest = nearest_maintenance_policy(_table(ON_TABLE), [_sales(ON_SALES)], _catalog(ON_CATALOG))

    assert nearest is not None
    assert (nearest.target.type, nearest.policy_id) == (PolicyTargetType.TABLE, ON_TABLE)


def test_the_namespace_beats_the_catalog():
    """A namespace's maintenance policy is nearer than the catalog's."""
    nearest = nearest_maintenance_policy(_table(), [_sales(ON_SALES)], _catalog(ON_CATALOG))

    assert nearest == NearestPolicy(
        target=PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("iceberg", "sales")), policy_id=ON_SALES
    )


def test_the_catalog_decides_when_nothing_nearer_holds_one():
    """With nothing nearer, the catalog's maintenance policy applies."""
    nearest = nearest_maintenance_policy(_table(), [_sales(None)], _catalog(ON_CATALOG))

    assert nearest is not None
    assert (nearest.target.type, nearest.policy_id) == (PolicyTargetType.CATALOG, ON_CATALOG)


def test_a_discovery_policy_does_not_count_for_maintenance():
    """A place holding only a discovery policy holds no maintenance policy: nothing applies."""
    table = _table()
    table.attach_discovery_policy(TableDiscoveryPolicyId.new(), NOW)

    assert nearest_maintenance_policy(table, [_sales(None)], _catalog(None)) is None
