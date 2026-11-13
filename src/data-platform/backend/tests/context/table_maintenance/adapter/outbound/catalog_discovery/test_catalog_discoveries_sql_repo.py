"""Test the repositories of the CatalogDiscovery aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.catalog_discovery.sql import (
    CatalogDiscoveriesSqlRepo,
    catalog_discoveries_table,
)
from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogDiscovery,
    CatalogDiscoveryId,
)
from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import (
    InMemoryCatalogDiscoveriesRepo,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

    from context.table_maintenance.application.port.outbound.catalog_discovery import CatalogDiscoveriesRepo

NOW = datetime(2026, 11, 14, 12, tzinfo=UTC)


@pytest.fixture(params=["sql", "memory"])
def repo(request: pytest.FixtureRequest, engine: Engine) -> CatalogDiscoveriesRepo:
    """Provide each repository implementation."""
    if request.param == "sql":
        return CatalogDiscoveriesSqlRepo(engine)
    return InMemoryCatalogDiscoveriesRepo()


def test_round_trip_keeps_the_catalog_and_time(repo: CatalogDiscoveriesRepo):
    """A stored discovery loads back equal, with an aware time."""
    saved = CatalogDiscovery.first("iceberg", NOW)
    repo.save(saved)

    loaded = repo.get(CatalogDiscoveryId("iceberg"))
    assert loaded is not None
    assert loaded.model_dump() == saved.model_dump()
    assert loaded.last_discovered_at.tzinfo is not None


def test_save_again_replaces_the_catalogs_discovery(repo: CatalogDiscoveriesRepo):
    """Saving a catalog's discovery again keeps one record per catalog, with the later time."""
    discovery = CatalogDiscovery.first("iceberg", NOW)
    repo.create(discovery)
    discovery.record(NOW + timedelta(minutes=10))
    repo.save(discovery)

    (only,) = repo.list_all()
    assert only.last_discovered_at == NOW + timedelta(minutes=10)


def test_unknown_catalog_is_none(repo: CatalogDiscoveriesRepo):
    """A catalog never discovered reads as None."""
    assert repo.get(CatalogDiscoveryId("nope")) is None


def test_list_all_is_by_catalog_name(repo: CatalogDiscoveriesRepo):
    """Every catalog's discovery is listed, by catalog name."""
    repo.save(CatalogDiscovery.first("lake", NOW))
    repo.save(CatalogDiscovery.first("iceberg", NOW))
    assert [d.catalog for d in repo.list_all()] == ["iceberg", "lake"]


def test_catalog_discoveries_sql_table_name():
    """The records live in the catalog_discoveries table."""
    assert catalog_discoveries_table.name == "catalog_discoveries"
