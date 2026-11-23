"""Test policy_candidates: the targets a request walks, nearest first."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from context.table_maintenance.application.domain.model.shared import PolicyTarget, PolicyTargetType, TableId
from context.table_maintenance.application.domain.model.table import Table, TableName
from context.table_maintenance.application.exceptions import NotFoundError, ValidationError
from context.table_maintenance.application.port.outbound.table import CatalogAccessDeniedError
from context.table_maintenance.application.service.shared import policy_candidates
from tests.context.table_maintenance.discovery_decision_samples import MANAGED
from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

NOW = datetime(2026, 11, 1, tzinfo=UTC)

ORDERS_CANDIDATES = (
    PolicyTarget(type=PolicyTargetType.TABLE, path=("prod", "sales", "eu", "orders"), table_uuid="u-1"),
    PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales", "eu")),
    PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("prod", "sales")),
    PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",)),
)


@pytest.fixture
def gateway() -> FakeReadTableMetadataGateway:
    """Provide a catalog prod holding sales.eu.orders (u-1)."""
    gateway = FakeReadTableMetadataGateway()
    gateway.add_table("prod", "sales.eu", "orders", "u-1")
    return gateway


@pytest.fixture
def tables() -> InMemoryTablesRepo:
    """Provide an empty tables repo."""
    return InMemoryTablesRepo()


def _candidates(gateway, tables, *, catalog=None, namespace=None, table=None, table_uuid=None):
    return policy_candidates(gateway, tables, catalog=catalog, namespace=namespace, table=table, table_uuid=table_uuid)


def test_a_uuid_alone_walks_from_the_recorded_table(gateway, tables):
    """A uuid without a catalog places the table by the name table maintenance records."""
    tables.create(
        Table.register(TableId("u-1"), TableName(catalog="prod", namespace="sales.eu", table="orders"), MANAGED, NOW)
    )
    assert _candidates(gateway, tables, table_uuid="u-1") == ORDERS_CANDIDATES


def test_a_uuid_alone_without_a_record_is_not_found(gateway, tables):
    """A uuid table maintenance has no record of is not found, though the catalog holds it."""
    with pytest.raises(NotFoundError):
        _candidates(gateway, tables, table_uuid="u-1")


def test_a_catalog_walks_only_the_catalog(gateway, tables):
    """A catalog alone is its own only candidate."""
    assert _candidates(gateway, tables, catalog="prod") == (
        PolicyTarget(type=PolicyTargetType.CATALOG, path=("prod",)),
    )


def test_a_namespace_walks_from_that_namespace(gateway, tables):
    """A namespace starts at itself, deepest first, then the catalog."""
    assert _candidates(gateway, tables, catalog="prod", namespace="sales.eu") == ORDERS_CANDIDATES[1:]


def test_a_place_is_walked_without_reading_the_catalog(gateway, tables):
    """A catalog or namespace is not checked for existence here; the caller decides (ruling F2)."""
    assert _candidates(gateway, tables, catalog="gone", namespace="nowhere") == (
        PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("gone", "nowhere")),
        PolicyTarget(type=PolicyTargetType.CATALOG, path=("gone",)),
    )
    assert gateway.calls == []


def test_a_table_by_name_takes_its_uuid_from_the_catalog(gateway, tables):
    """A table named by location is loaded from the catalog, so it need not be recorded."""
    assert _candidates(gateway, tables, catalog="prod", namespace="sales.eu", table="orders") == ORDERS_CANDIDATES


def test_a_table_by_name_with_its_uuid_given_is_not_loaded(gateway, tables):
    """A caller holding the uuid is trusted and the catalog is not read."""
    assert (
        _candidates(gateway, tables, catalog="prod", namespace="sales.eu", table="orders", table_uuid="u-1")
        == ORDERS_CANDIDATES
    )
    assert gateway.calls == []


def test_a_table_missing_from_the_catalog_is_not_found(gateway, tables):
    """A table the catalog does not hold is not found."""
    with pytest.raises(NotFoundError):
        _candidates(gateway, tables, catalog="prod", namespace="sales.eu", table="missing")


def test_a_table_in_a_dropped_catalog_is_not_found(gateway, tables):
    """A catalog the server no longer has reads as not found."""
    gateway.drop_catalog("prod")
    with pytest.raises(NotFoundError):
        _candidates(gateway, tables, catalog="prod", namespace="sales.eu", table="orders")


def test_a_table_in_a_refused_catalog_is_access_denied(gateway, tables):
    """A catalog the platform cannot read stays a refusal."""
    gateway.deny("prod")
    with pytest.raises(CatalogAccessDeniedError):
        _candidates(gateway, tables, catalog="prod", namespace="sales.eu", table="orders")


def test_a_table_needs_its_namespace(gateway, tables):
    """A table named without a namespace is refused."""
    with pytest.raises(ValidationError, match="a table needs its namespace"):
        _candidates(gateway, tables, catalog="prod", table="orders")


def test_neither_a_catalog_nor_a_uuid_is_refused(gateway, tables):
    """A request naming no catalog and no uuid is refused."""
    with pytest.raises(ValidationError, match="name a catalog or a table uuid"):
        _candidates(gateway, tables)
