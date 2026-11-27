"""Test nearest_discovery_policy: the table, then its namespaces deepest first, then its catalog."""

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
)
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.domain.service.shared import NearestPolicy, nearest_discovery_policy

NOW = datetime(2026, 11, 1, tzinfo=UTC)
ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders")
ON_TABLE = TableDiscoveryPolicyId.new()
ON_EU = TableDiscoveryPolicyId.new()
ON_SALES = TableDiscoveryPolicyId.new()
ON_CATALOG = TableDiscoveryPolicyId.new()


def _table(policy: TableDiscoveryPolicyId | None = None, name: TableName = ORDERS) -> Table:
    table = Table.register_undecided(TableId("u1"), name, NOW)
    if policy is not None:
        table.attach_discovery_policy(policy, NOW)
    return table


def _namespace(levels: tuple[str, ...], policy: TableDiscoveryPolicyId | None, catalog: str = "iceberg") -> Namespace:
    namespace = Namespace.register(NamespaceId.of(catalog, levels), NOW)
    if policy is not None:
        namespace.attach_discovery_policy(policy, NOW)
    return namespace


def _catalog(policy: TableDiscoveryPolicyId | None, name: str = "iceberg") -> Catalog:
    catalog = Catalog.register(CatalogId(name), NOW)
    if policy is not None:
        catalog.attach_discovery_policy(policy, NOW)
    return catalog


def _namespace_target(*levels: str) -> PolicyTarget:
    return PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("iceberg", *levels))


def test_the_tables_own_policy_beats_its_namespaces():
    """A policy attached to the table itself is nearer than any namespace's."""
    nearest = nearest_discovery_policy(_table(ON_TABLE), [_namespace(("sales", "eu"), ON_EU)], _catalog(ON_CATALOG))

    assert nearest == NearestPolicy(
        target=PolicyTarget(type=PolicyTargetType.TABLE, path=("iceberg", "sales", "eu", "orders"), table_uuid="u1"),
        policy_id=ON_TABLE,
    )


def test_the_deeper_namespace_beats_the_shallower_one_whatever_their_order():
    """``sales.eu`` is nearer to ``sales.eu.orders`` than ``sales``, even when listed after it."""
    nearest = nearest_discovery_policy(
        _table(), [_namespace(("sales",), ON_SALES), _namespace(("sales", "eu"), ON_EU)], _catalog(ON_CATALOG)
    )

    assert nearest == NearestPolicy(target=_namespace_target("sales", "eu"), policy_id=ON_EU)


def test_a_namespace_holding_no_discovery_policy_is_passed_over():
    """A namespace that holds none is skipped, and the next one up decides."""
    nearest = nearest_discovery_policy(
        _table(), [_namespace(("sales", "eu"), None), _namespace(("sales",), ON_SALES)], None
    )

    assert nearest == NearestPolicy(target=_namespace_target("sales"), policy_id=ON_SALES)


def test_the_namespace_beats_the_catalog():
    """A namespace's policy is nearer than the catalog's."""
    nearest = nearest_discovery_policy(_table(), [_namespace(("sales",), ON_SALES)], _catalog(ON_CATALOG))

    assert nearest == NearestPolicy(target=_namespace_target("sales"), policy_id=ON_SALES)


def test_the_catalog_decides_when_nothing_nearer_holds_a_policy():
    """With nothing on the table or its namespaces, the catalog's policy applies."""
    nearest = nearest_discovery_policy(_table(), [_namespace(("sales",), None)], _catalog(ON_CATALOG))

    assert nearest == NearestPolicy(
        target=PolicyTarget(type=PolicyTargetType.CATALOG, path=("iceberg",)), policy_id=ON_CATALOG
    )


def test_nothing_held_anywhere_gives_none():
    """No policy on the table, its namespaces or its catalog: no discovery policy applies."""
    assert nearest_discovery_policy(_table(), [_namespace(("sales",), None)], _catalog(None)) is None
    assert nearest_discovery_policy(None, [], None) is None


def test_a_namespace_that_does_not_enclose_the_table_is_ignored():
    """A sibling namespace, a deeper one, or one of another catalog never applies to the table."""
    nearest = nearest_discovery_policy(
        _table(),
        [
            _namespace(("sales", "us"), ON_EU),
            _namespace(("sales", "eu", "archive"), ON_EU),
            _namespace(("sales",), ON_EU, catalog="other"),
            _namespace(("sal",), ON_EU),
        ],
        _catalog(ON_CATALOG),
    )

    assert nearest is not None
    assert nearest.policy_id == ON_CATALOG


def test_without_a_table_every_namespace_given_is_walked():
    """For a place that is no table, the namespaces given are walked deepest first, then the catalog."""
    nearest = nearest_discovery_policy(
        None, [_namespace(("sales",), ON_SALES), _namespace(("sales", "eu"), ON_EU)], _catalog(ON_CATALOG)
    )

    assert nearest == NearestPolicy(target=_namespace_target("sales", "eu"), policy_id=ON_EU)


def test_the_current_name_places_a_table_that_moved():
    """A table read under a new name is walked from its new namespace, keeping its own policy."""
    stale = _table(name=TableName(catalog="iceberg", namespace="staging", table="orders"))
    moved = nearest_discovery_policy(stale, [_namespace(("sales", "eu"), ON_EU)], None, name=ORDERS)

    assert moved == NearestPolicy(target=_namespace_target("sales", "eu"), policy_id=ON_EU)
    own = nearest_discovery_policy(_table(ON_TABLE, name=stale.name), [], None, name=ORDERS)
    assert own is not None
    assert own.target.path == ("iceberg", "sales", "eu", "orders")


def test_a_catalog_of_another_name_is_ignored_for_a_table():
    """The catalog given applies only when it is the table's own."""
    assert nearest_discovery_policy(_table(), [], _catalog(ON_CATALOG, name="other")) is None
