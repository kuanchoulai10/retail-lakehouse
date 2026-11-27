"""Test the repositories of the Catalog aggregate, the SQL one and the in-memory fake alike."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from context.table_maintenance.adapter.outbound.catalog.sql import CatalogsSqlRepo, catalogs_table
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.adapter.outbound.table_discovery_policy.sql import TableDiscoveryPoliciesSqlRepo
from context.table_maintenance.application.domain.model.catalog import Catalog
from context.table_maintenance.application.domain.model.shared import (
    CatalogId,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryRule,
    DiscoveryRules,
    RuleAction,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
    TableNamePattern,
)
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError
from tests.context.table_maintenance.fakes.in_memory_catalogs_repo import InMemoryCatalogsRepo

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.catalog import CatalogsRepo

NOW = datetime(2026, 11, 27, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)
SALES = TableDiscoveryPolicyId("dp-00000000000000000000000001")
NIGHTLY = TableMaintenancePolicyId("mp-00000000000000000000000001")


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> CatalogsRepo:
    """Provide each catalogs repository implementation."""
    if request.param == "sql":
        return CatalogsSqlRepo(engine)
    return InMemoryCatalogsRepo()


def _catalog(name: str = "iceberg") -> Catalog:
    return Catalog.register(CatalogId(name), NOW)


def test_a_created_catalog_reads_back_equal(repo: CatalogsRepo):
    """Every field of a stored catalog, its two policies included, reads back."""
    catalog = _catalog()
    catalog.attach_discovery_policy(SALES, LATER)
    catalog.attach_maintenance_policy(NIGHTLY, LATER)
    repo.create(catalog)
    loaded = repo.get(CatalogId("iceberg"))
    assert loaded is not None
    assert loaded.model_dump() == catalog.model_dump()
    assert loaded.discovery_policy_id == SALES
    assert loaded.maintenance_policy_id == NIGHTLY
    assert loaded.version == 1
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at == LATER


def test_a_catalog_holding_no_policy_reads_back_without_one(repo: CatalogsRepo):
    """A catalog with neither policy reads back with neither."""
    repo.create(_catalog())
    loaded = repo.get(CatalogId("iceberg"))
    assert loaded is not None
    assert loaded.discovery_policy_id is None
    assert loaded.maintenance_policy_id is None


def test_get_of_an_unknown_catalog_is_none(repo: CatalogsRepo):
    """A catalog never stored reads as None."""
    assert repo.get(CatalogId("ghost")) is None


def test_create_of_a_stored_catalog_is_a_conflict(repo: CatalogsRepo):
    """One record per catalog: a second create of the same name raises ConflictError."""
    repo.create(_catalog())
    with pytest.raises(ConflictError):
        repo.create(_catalog())


def test_get_many_returns_the_stored_catalogs_among_the_ids(repo: CatalogsRepo):
    """get_many returns the catalogs that exist among the ids and skips the others."""
    repo.create(_catalog("iceberg"))
    repo.create(_catalog("lake"))
    repo.create(_catalog("other"))
    found = repo.get_many([CatalogId("lake"), CatalogId("iceberg"), CatalogId("ghost")])
    assert sorted(c.id.value for c in found) == ["iceberg", "lake"]
    assert repo.get_many([]) == []


def test_list_all_is_ordered_by_name(repo: CatalogsRepo):
    """Every catalog is listed, by name."""
    repo.create(_catalog("lake"))
    repo.create(_catalog("iceberg"))
    assert [c.id.value for c in repo.list_all()] == ["iceberg", "lake"]


def test_update_saves_the_change_at_the_next_version(repo: CatalogsRepo):
    """A save of the stored version is stored and returned at the next version; the caller's copy stays."""
    repo.create(_catalog())
    catalog = repo.get(CatalogId("iceberg"))
    assert catalog is not None
    catalog.attach_discovery_policy(SALES, LATER)
    saved = repo.update(catalog)
    assert saved is not catalog
    assert saved.version == 2
    assert catalog.version == 1
    loaded = repo.get(CatalogId("iceberg"))
    assert loaded is not None
    assert loaded.discovery_policy_id == SALES
    assert loaded.updated_at == LATER
    assert loaded.version == 2
    assert repo.update(saved).version == 3


def test_update_from_a_stale_copy_is_refused(repo: CatalogsRepo):
    """Of two copies read at one version, the second save is refused and the first one's change stays stored."""
    repo.create(_catalog())
    a = repo.get(CatalogId("iceberg"))
    b = repo.get(CatalogId("iceberg"))
    assert a is not None
    assert b is not None
    a.attach_discovery_policy(SALES, LATER)
    repo.update(a)
    b.attach_maintenance_policy(NIGHTLY, LATER)
    with pytest.raises(ConcurrentUpdateError, match="catalog iceberg was changed by someone else"):
        repo.update(b)
    loaded = repo.get(CatalogId("iceberg"))
    assert loaded is not None
    assert loaded.discovery_policy_id == SALES
    assert loaded.maintenance_policy_id is None
    assert loaded.version == 2


def test_update_of_an_unknown_catalog_raises_lookup_error(repo: CatalogsRepo):
    """A save of a catalog never stored is a LookupError, not a conflict."""
    with pytest.raises(LookupError, match="catalog ghost does not exist"):
        repo.update(_catalog("ghost"))


def test_the_version_is_stored_in_its_column(engine: Engine):
    """The version is a column of the row, written 1 on create and moved by each save."""
    repo = CatalogsSqlRepo(engine)
    catalog = _catalog()
    repo.create(catalog)
    repo.update(catalog)
    with engine.connect() as connection:
        row = connection.execute(catalogs_table.select()).mappings().one()
    assert row["name"] == "iceberg"
    assert row["version"] == 2


def test_a_policy_attached_to_a_catalog_cannot_be_deleted():
    """The catalog's discovery policy column references the policy, so deleting the policy is refused."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    create_schema(engine)
    policies = TableDiscoveryPoliciesSqlRepo(engine)
    rules = DiscoveryRules(
        rules=(DiscoveryRule(action=RuleAction.INCLUDE, table_name_pattern=TableNamePattern(value="*")),)
    )
    policy = TableDiscoveryPolicy.create(TableDiscoveryPolicyName(value="all"), "every table", rules, NOW)
    policies.create(policy)
    catalog = _catalog()
    catalog.attach_discovery_policy(policy.id, LATER)
    CatalogsSqlRepo(engine).create(catalog)
    with pytest.raises(ConflictError) as refused:
        policies.delete(policy.id)
    assert isinstance(refused.value.__cause__, IntegrityError)
    assert policies.get(policy.id) is not None


def test_a_catalog_cannot_hold_a_policy_that_does_not_exist():
    """With foreign keys enforced, a catalog naming an unknown policy is refused when created or saved."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda dbapi_connection, _: dbapi_connection.execute("PRAGMA foreign_keys=ON"))
    create_schema(engine)
    repo = CatalogsSqlRepo(engine)
    catalog = _catalog()
    catalog.attach_maintenance_policy(NIGHTLY, LATER)
    with pytest.raises(ConflictError):
        repo.create(catalog)
    repo.create(_catalog())
    stored = repo.get(CatalogId("iceberg"))
    assert stored is not None
    stored.attach_maintenance_policy(NIGHTLY, LATER)
    with pytest.raises(ConflictError):
        repo.update(stored)
    loaded = repo.get(CatalogId("iceberg"))
    assert loaded is not None
    assert loaded.maintenance_policy_id is None
    assert loaded.version == 1
