"""Test the repositories of the Namespace aggregate, the SQL one and the in-memory fake alike."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

from context.table_maintenance.adapter.outbound.namespace.sql import NamespacesSqlRepo, namespaces_table
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.domain.model.namespace import Namespace
from context.table_maintenance.application.domain.model.shared import (
    NamespaceId,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError
from tests.context.table_maintenance.fakes.in_memory_namespaces_repo import InMemoryNamespacesRepo

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.namespace import NamespacesRepo

NOW = datetime(2026, 11, 27, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)
SALES = TableDiscoveryPolicyId("dp-00000000000000000000000001")
NIGHTLY = TableMaintenancePolicyId("mp-00000000000000000000000001")
SALES_EU = NamespaceId.of("iceberg", ("sales", "eu.west"))


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> NamespacesRepo:
    """Provide each namespaces repository implementation."""
    if request.param == "sql":
        return NamespacesSqlRepo(engine)
    return InMemoryNamespacesRepo()


def _namespace(catalog: str = "iceberg", *levels: str) -> Namespace:
    return Namespace.register(NamespaceId.of(catalog, levels or ("sales", "eu.west")), NOW)


def test_a_created_namespace_reads_back_equal(repo: NamespacesRepo):
    """Every field of a stored namespace, its levels and its two policies included, reads back."""
    namespace = _namespace()
    namespace.attach_discovery_policy(SALES, LATER)
    namespace.attach_maintenance_policy(NIGHTLY, LATER)
    repo.create(namespace)
    loaded = repo.get(SALES_EU)
    assert loaded is not None
    assert loaded.model_dump() == namespace.model_dump()
    assert loaded.levels == ("sales", "eu.west")
    assert loaded.discovery_policy_id == SALES
    assert loaded.maintenance_policy_id == NIGHTLY
    assert loaded.created_at.tzinfo is not None


def test_get_of_an_unknown_namespace_is_none(repo: NamespacesRepo):
    """A namespace never stored reads as None."""
    assert repo.get(SALES_EU) is None


def test_create_of_a_stored_namespace_is_a_concurrent_update(repo: NamespacesRepo):
    """One record per namespace: a second create of the same one lost a race, so the caller retries it."""
    repo.create(_namespace())
    with pytest.raises(ConcurrentUpdateError, match="^namespace sales.eu.west of iceberg was changed by someone else$"):
        repo.create(_namespace())


def test_get_many_returns_the_stored_namespaces_among_the_ids(repo: NamespacesRepo):
    """get_many returns the namespaces that exist among the ids and skips the others."""
    repo.create(_namespace("iceberg", "sales"))
    repo.create(_namespace("iceberg", "sales", "eu.west"))
    repo.create(_namespace("lake", "sales"))
    found = repo.get_many([SALES_EU, NamespaceId.of("lake", ("sales",)), NamespaceId.of("lake", ("ghost",))])
    assert sorted(n.id.value for n in found) == sorted([SALES_EU.value, NamespaceId.of("lake", ("sales",)).value])
    assert repo.get_many([]) == []


def test_list_in_catalog_returns_only_that_catalogs_namespaces_outermost_first(repo: NamespacesRepo):
    """list_in_catalog lists the namespaces of one catalog, a parent before its children."""
    repo.create(_namespace("iceberg", "sales", "eu.west"))
    repo.create(_namespace("lake", "sales"))
    repo.create(_namespace("iceberg", "sales"))
    repo.create(_namespace("iceberg", "finance"))
    assert [n.levels for n in repo.list_in_catalog("iceberg")] == [("finance",), ("sales",), ("sales", "eu.west")]
    assert [n.levels for n in repo.list_in_catalog("lake")] == [("sales",)]
    assert repo.list_in_catalog("ghost") == []


def test_list_in_catalog_does_not_match_a_catalog_name_by_prefix(repo: NamespacesRepo):
    """A catalog whose name starts with another's does not lend it its namespaces."""
    repo.create(_namespace("ice", "sales"))
    repo.create(_namespace("iceberg", "sales"))
    assert [n.catalog for n in repo.list_in_catalog("ice")] == ["ice"]


def test_list_all_lists_every_namespace_by_catalog_then_levels(repo: NamespacesRepo):
    """Every namespace is listed, by catalog and then by levels."""
    repo.create(_namespace("lake", "sales"))
    repo.create(_namespace("iceberg", "sales"))
    assert [(n.catalog, n.levels) for n in repo.list_all()] == [("iceberg", ("sales",)), ("lake", ("sales",))]


def test_update_saves_the_change_at_the_next_version(repo: NamespacesRepo):
    """A save of the stored version is stored and returned at the next version."""
    repo.create(_namespace())
    namespace = repo.get(SALES_EU)
    assert namespace is not None
    namespace.attach_maintenance_policy(NIGHTLY, LATER)
    saved = repo.update(namespace)
    assert saved.version == 2
    assert namespace.version == 1
    loaded = repo.get(SALES_EU)
    assert loaded is not None
    assert loaded.maintenance_policy_id == NIGHTLY
    assert loaded.version == 2


def test_update_from_a_stale_copy_is_refused(repo: NamespacesRepo):
    """Of two copies read at one version, the second save is refused and the first one's change stays stored."""
    repo.create(_namespace())
    a = repo.get(SALES_EU)
    b = repo.get(SALES_EU)
    assert a is not None
    assert b is not None
    a.attach_discovery_policy(SALES, LATER)
    repo.update(a)
    b.attach_maintenance_policy(NIGHTLY, LATER)
    with pytest.raises(ConcurrentUpdateError, match="namespace sales.eu.west of iceberg was changed by someone else"):
        repo.update(b)
    loaded = repo.get(SALES_EU)
    assert loaded is not None
    assert loaded.discovery_policy_id == SALES
    assert loaded.maintenance_policy_id is None


def test_update_of_an_unknown_namespace_raises_lookup_error(repo: NamespacesRepo):
    """A save of a namespace never stored is a LookupError, not a conflict."""
    with pytest.raises(LookupError, match="does not exist"):
        repo.update(_namespace())


def test_the_row_holds_the_catalog_and_the_levels(engine: Engine):
    """The row keeps the catalog in its own column and the levels as a JSON list, beside the version."""
    repo = NamespacesSqlRepo(engine)
    namespace = _namespace()
    repo.create(namespace)
    repo.update(namespace)
    with engine.connect() as connection:
        row = connection.execute(namespaces_table.select()).mappings().one()
    assert row["id"] == SALES_EU.value
    assert row["catalog"] == "iceberg"
    assert row["path_json"] == ["sales", "eu.west"]
    assert row["version"] == 2


def test_a_namespace_cannot_hold_a_policy_that_does_not_exist():
    """With foreign keys enforced, a namespace naming an unknown policy is refused when created or saved."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    create_schema(engine)
    repo = NamespacesSqlRepo(engine)
    namespace = _namespace()
    namespace.attach_discovery_policy(SALES, LATER)
    gone = f"^discovery policy {SALES.value} held by namespace sales.eu.west of iceberg no longer exists$"
    with pytest.raises(ConflictError, match=gone):
        repo.create(namespace)
    repo.create(_namespace())
    stored = repo.get(SALES_EU)
    assert stored is not None
    stored.attach_discovery_policy(SALES, LATER)
    with pytest.raises(ConflictError, match=gone):
        repo.update(stored)
    loaded = repo.get(SALES_EU)
    assert loaded is not None
    assert loaded.discovery_policy_id is None
