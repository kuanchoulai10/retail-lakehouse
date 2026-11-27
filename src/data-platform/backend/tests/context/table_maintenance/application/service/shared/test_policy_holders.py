"""Test PolicyHolders.of_place: the records a request's place walks, and each kind's nearest policy on them."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

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
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.outbound.table import CatalogAccessDeniedError
from context.table_maintenance.application.service.shared import PolicyHolders
from tests.context.table_maintenance.discovery_decision_samples import MANAGED
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

NOW = datetime(2026, 11, 1, tzinfo=UTC)
ORDERS_NAME = TableName(catalog="prod", namespace="sales.eu", table="orders")
GOLD = TableMaintenancePolicyId("mp-01m7sd16b1ef2vww335cwcg9k8")
EU_TABLES = TableDiscoveryPolicyId("dp-01m7sd16b1ef2vww335cwcg9k8")


class _Places:
    """Catalog prod holding sales.eu.orders (u-1); the catalog and both namespaces are recorded, the table is not."""

    def __init__(self) -> None:
        self.gateway = FakeReadTableMetadataGateway()
        self.gateway.add_table("prod", "sales.eu", "orders", "u-1")
        self.tables = InMemoryTablesRepo()
        self.catalogs = InMemoryCatalogsRepo()
        self.namespaces = InMemoryNamespacesRepo()
        self.catalogs.create(Catalog.register(CatalogId("prod"), NOW))
        for levels in (("sales",), ("sales", "eu"), ("sales", "us")):
            self.namespaces.create(Namespace.register(NamespaceId.of("prod", levels), NOW))

    def of(
        self,
        *,
        catalog: str | None = None,
        namespace: str | None = None,
        table: str | None = None,
        table_uuid: str | None = None,
    ) -> PolicyHolders:
        return PolicyHolders.of_place(
            self.gateway,
            self.tables,
            self.catalogs,
            self.namespaces,
            catalog=catalog,
            namespace=namespace,
            table=table,
            table_uuid=table_uuid,
        )

    def record_orders(self) -> Table:
        table = Table.register(TableId("u-1"), ORDERS_NAME, MANAGED, NOW)
        self.tables.create(table)
        return table


@pytest.fixture
def places() -> _Places:
    """Provide the recorded places of catalog prod."""
    return _Places()


def _levels(holders: PolicyHolders) -> list[tuple[str, ...]]:
    return sorted(n.levels for n in holders.namespaces)


def test_a_uuid_alone_walks_from_the_recorded_table(places: _Places) -> None:
    """A uuid without a catalog places the table by the name table maintenance records."""
    places.record_orders()

    holders = places.of(table_uuid="u-1")

    assert holders.table is not None
    assert (holders.table.id.value, holders.name, _levels(holders)) == (
        "u-1",
        ORDERS_NAME,
        [("sales",), ("sales", "eu")],
    )
    assert holders.catalog is not None


def test_a_uuid_alone_without_a_record_is_not_found(places: _Places) -> None:
    """A uuid table maintenance has no record of is not found, though the catalog holds it."""
    with pytest.raises(NotFoundError):
        places.of(table_uuid="u-1")


def test_a_catalog_walks_only_the_catalog(places: _Places) -> None:
    """A catalog alone reads no namespace and no table."""
    holders = places.of(catalog="prod")

    assert (holders.table, holders.name, holders.namespaces) == (None, None, ())
    assert holders.catalog is not None


def test_a_namespace_walks_from_that_namespace_and_reads_no_sibling(places: _Places) -> None:
    """A namespace reads itself and the namespaces above it, never a sibling, in one read."""
    holders = places.of(catalog="prod", namespace="sales.eu")

    assert (holders.table, holders.name, _levels(holders)) == (None, None, [("sales",), ("sales", "eu")])


def test_a_place_is_walked_without_reading_the_catalog(places: _Places) -> None:
    """A catalog or namespace is not checked for existence here; the caller decides."""
    holders = places.of(catalog="gone", namespace="nowhere")

    assert (holders.catalog, holders.namespaces) == (None, ())
    assert places.gateway.calls == []


def test_a_table_by_name_takes_its_uuid_from_the_catalog(places: _Places) -> None:
    """A table named by location is loaded from the catalog, so it need not be recorded."""
    holders = places.of(catalog="prod", namespace="sales.eu", table="orders")

    assert (holders.table, holders.name, _levels(holders)) == (None, ORDERS_NAME, [("sales",), ("sales", "eu")])


def test_a_table_by_name_reads_its_record_by_the_uuid(places: _Places) -> None:
    """A recorded table is found by the uuid the catalog gives it."""
    places.record_orders()

    holders = places.of(catalog="prod", namespace="sales.eu", table="orders")

    assert holders.table is not None
    assert holders.table.id.value == "u-1"


def test_a_table_by_name_with_its_uuid_given_is_not_loaded(places: _Places) -> None:
    """A caller holding the uuid is trusted and the catalog is not read."""
    places.record_orders()

    holders = places.of(catalog="prod", namespace="sales.eu", table="orders", table_uuid="u-1")

    assert holders.table is not None
    assert places.gateway.calls == []


def test_a_table_missing_from_the_catalog_is_not_found(places: _Places) -> None:
    """A table the catalog does not hold is not found."""
    with pytest.raises(NotFoundError):
        places.of(catalog="prod", namespace="sales.eu", table="missing")


def test_a_table_in_a_dropped_catalog_is_not_found(places: _Places) -> None:
    """A catalog the server no longer has reads as not found."""
    places.gateway.drop_catalog("prod")
    with pytest.raises(NotFoundError):
        places.of(catalog="prod", namespace="sales.eu", table="orders")


def test_a_table_in_a_refused_catalog_is_access_denied(places: _Places) -> None:
    """A catalog the platform cannot read stays a refusal."""
    places.gateway.deny("prod")
    with pytest.raises(CatalogAccessDeniedError):
        places.of(catalog="prod", namespace="sales.eu", table="orders")


def test_a_table_needs_its_namespace(places: _Places) -> None:
    """A table named without a namespace is refused."""
    with pytest.raises(ValidationError, match="a table needs its namespace"):
        places.of(catalog="prod", table="orders")


def test_neither_a_catalog_nor_a_uuid_is_refused(places: _Places) -> None:
    """A request naming no catalog and no uuid is refused."""
    with pytest.raises(ValidationError, match="name a catalog or a table uuid"):
        places.of()


def test_each_kind_finds_its_own_nearest_holder(places: _Places) -> None:
    """The table's maintenance policy wins for maintenance; discovery still answers from the namespace."""
    table = places.record_orders()
    table.attach_maintenance_policy(GOLD, NOW)
    places.tables.update(table)
    namespace = places.namespaces.get(NamespaceId.of("prod", ("sales",)))
    assert namespace is not None
    namespace.attach_discovery_policy(EU_TABLES, NOW)
    places.namespaces.update(namespace)

    holders = places.of(table_uuid="u-1")

    maintenance, discovery = holders.nearest_maintenance_policy(), holders.nearest_discovery_policy()
    assert maintenance is not None
    assert discovery is not None
    assert (maintenance.policy_id, maintenance.target) == (
        GOLD,
        PolicyTarget(type=PolicyTargetType.TABLE, path=("prod", "sales", "eu", "orders"), table_uuid="u-1"),
    )
    assert (discovery.policy_id, discovery.target) == (
        EU_TABLES,
        PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales")),
    )
