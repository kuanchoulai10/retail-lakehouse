"""Test the repositories of the CatalogDiscovery aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.catalog_discovery.sql import (
    CatalogDiscoveriesSqlRepo,
    catalog_discoveries_table,
)
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogDiscovery,
    CatalogDiscoveryId,
    CatalogScanFailure,
    CatalogScanFailureReason,
)
from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import (
    InMemoryCatalogDiscoveriesRepo,
)

if TYPE_CHECKING:
    from pathlib import Path

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
    assert loaded.last_discovered_at is not None
    assert loaded.last_discovered_at.tzinfo is not None


def test_save_again_replaces_the_catalogs_discovery(repo: CatalogDiscoveriesRepo):
    """Saving a catalog's discovery again keeps one record per catalog, with the later time."""
    discovery = CatalogDiscovery.first("iceberg", NOW)
    repo.create(discovery)
    discovery.record(NOW + timedelta(minutes=10))
    repo.save(discovery)

    (only,) = repo.list_all()
    assert only.last_discovered_at == NOW + timedelta(minutes=10)


def test_an_older_scan_saved_last_does_not_move_the_time_back(repo: CatalogDiscoveriesRepo):
    """Two scans of one catalog that overlap: the one that started earlier, saved last, does not win."""
    repo.save(CatalogDiscovery.first("iceberg", NOW + timedelta(minutes=10)))
    repo.save(CatalogDiscovery.first("iceberg", NOW))

    (only,) = repo.list_all()
    assert only.last_discovered_at == NOW + timedelta(minutes=10)


def test_a_first_scan_saved_after_another_writer_inserted_is_no_error(repo: CatalogDiscoveriesRepo):
    """A scan that read no record, saved after another scan inserted one, moves the time forward without failing."""
    repo.save(CatalogDiscovery.first("iceberg", NOW))
    repo.save(CatalogDiscovery.first("iceberg", NOW + timedelta(minutes=10)))

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


def test_a_scan_that_loses_the_insert_race_moves_the_time_forward(engine: Engine, monkeypatch: pytest.MonkeyPatch):
    """Both scans found no row; the one whose insert hits the other's row tries again and moves the time forward."""
    repo = CatalogDiscoveriesSqlRepo(engine)
    original = repo._save_once
    calls: list[datetime | None] = []

    def racing(entity: CatalogDiscovery) -> None:
        calls.append(entity.last_discovered_at)
        if len(calls) == 1:
            original(CatalogDiscovery.first("iceberg", NOW))
            raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed: catalog_discoveries.catalog"))
        original(entity)

    monkeypatch.setattr(repo, "_save_once", racing)
    repo.save(CatalogDiscovery.first("iceberg", NOW + timedelta(minutes=10)))

    assert len(calls) == 2
    loaded = repo.get(CatalogDiscoveryId("iceberg"))
    assert loaded is not None
    assert loaded.last_discovered_at == NOW + timedelta(minutes=10)


def _failure(at: datetime, reason: CatalogScanFailureReason = CatalogScanFailureReason.CANNOT_ACCESS):
    return CatalogScanFailure(reason=reason, detail=f"{reason.value} at {at.isoformat()}", failed_at=at)


def test_a_catalog_that_only_failed_round_trips(repo: CatalogDiscoveriesRepo):
    """A catalog never scanned but refused is stored with no scan time and loads back equal."""
    saved = CatalogDiscovery.failed("iceberg", _failure(NOW))
    repo.save(saved)

    loaded = repo.get(CatalogDiscoveryId("iceberg"))
    assert loaded is not None
    assert loaded.model_dump() == saved.model_dump()
    assert loaded.last_discovered_at is None
    assert loaded.last_failure is not None
    assert loaded.last_failure.reason is CatalogScanFailureReason.CANNOT_ACCESS
    assert loaded.last_failure.failed_at.tzinfo is not None


def test_failure_and_success_times_move_forward_independently(repo: CatalogDiscoveriesRepo):
    """An older failure never overwrites a newer one, an older scan never a newer one, and each moves on its own."""
    later = NOW + timedelta(minutes=10)
    repo.save(CatalogDiscovery.failed("iceberg", _failure(later, CatalogScanFailureReason.NOT_FOUND)))
    repo.save(CatalogDiscovery.failed("iceberg", _failure(NOW)))
    repo.save(CatalogDiscovery.first("iceberg", later))
    repo.save(CatalogDiscovery.first("iceberg", NOW))

    loaded = repo.get(CatalogDiscoveryId("iceberg"))
    assert loaded is not None
    assert loaded.last_discovered_at == later
    assert loaded.last_failure == _failure(later, CatalogScanFailureReason.NOT_FOUND)


def test_a_newer_failure_replaces_the_stored_one_and_keeps_the_scan_time(repo: CatalogDiscoveriesRepo):
    """A failure after the last scan is stored with its reason and detail; the scan time stays."""
    repo.save(CatalogDiscovery.first("iceberg", NOW))
    repo.save(CatalogDiscovery.failed("iceberg", _failure(NOW + timedelta(minutes=5))))
    repo.save(
        CatalogDiscovery.failed("iceberg", _failure(NOW + timedelta(minutes=10), CatalogScanFailureReason.NOT_FOUND))
    )

    loaded = repo.get(CatalogDiscoveryId("iceberg"))
    assert loaded is not None
    assert loaded.last_discovered_at == NOW
    assert loaded.current_failure == _failure(NOW + timedelta(minutes=10), CatalogScanFailureReason.NOT_FOUND)


def test_a_scan_after_a_failure_makes_it_not_current(repo: CatalogDiscoveriesRepo):
    """A completed scan saved after a failure clears the current failure and keeps the failure."""
    repo.save(CatalogDiscovery.failed("iceberg", _failure(NOW)))
    repo.save(CatalogDiscovery.first("iceberg", NOW + timedelta(minutes=10)))

    loaded = repo.get(CatalogDiscoveryId("iceberg"))
    assert loaded is not None
    assert loaded.current_failure is None
    assert loaded.last_failure == _failure(NOW)


def test_an_older_catalog_discoveries_table_gains_the_failure_columns(tmp_path: Path) -> None:
    """A table stored before failures were recorded gets their columns when the schema is created again."""
    engine = create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE catalog_discoveries (catalog VARCHAR PRIMARY KEY, last_discovered_at VARCHAR NOT NULL)")
        )
    create_schema(engine)
    columns = {c["name"] for c in inspect(engine).get_columns("catalog_discoveries")}
    assert {"failure_reason", "failure_detail", "failed_at"} <= columns
