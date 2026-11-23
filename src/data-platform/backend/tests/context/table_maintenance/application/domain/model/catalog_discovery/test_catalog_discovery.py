"""Test the CatalogDiscovery aggregate: when discovery last scanned a whole catalog, and its last failure."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogDiscovery,
    CatalogScanFailure,
    CatalogScanFailureReason,
)
from context.table_maintenance.application.domain.model.shared import CatalogDiscoveryId

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(minutes=10)


def test_a_first_discovery_records_its_catalog_and_time():
    """The first scan of a catalog records when it ran, under the catalog's name."""
    discovery = CatalogDiscovery.first("iceberg", T0)
    assert discovery.id == CatalogDiscoveryId("iceberg")
    assert discovery.catalog == "iceberg"
    assert discovery.last_discovered_at == T0


def test_a_later_discovery_moves_the_time_forward():
    """Each later scan records its time."""
    discovery = CatalogDiscovery.first("iceberg", T0)
    discovery.record(T1)
    assert discovery.last_discovered_at == T1


def test_an_older_discovery_does_not_move_the_time_back():
    """A scan that started before the recorded one finished late; the time never moves back."""
    discovery = CatalogDiscovery.first("iceberg", T1)
    discovery.record(T0)
    assert discovery.last_discovered_at == T1


def test_a_catalog_discovery_needs_a_catalog_name():
    """An empty catalog name is refused."""
    with pytest.raises(InvariantViolation):
        CatalogDiscovery.first("", T0)


def _refused(at: datetime) -> CatalogScanFailure:
    return CatalogScanFailure(
        reason=CatalogScanFailureReason.CANNOT_ACCESS,
        detail="the platform's catalog credential cannot read catalog iceberg",
        failed_at=at,
    )


def _missing(at: datetime) -> CatalogScanFailure:
    return CatalogScanFailure(
        reason=CatalogScanFailureReason.NOT_FOUND, detail="catalog iceberg not found", failed_at=at
    )


def test_a_catalog_whose_first_scan_failed_has_a_failure_and_no_scan_time():
    """A catalog the first scan could not read records the failure and no scan time."""
    discovery = CatalogDiscovery.failed("iceberg", _refused(T0))
    assert discovery.catalog == "iceberg"
    assert discovery.last_discovered_at is None
    assert discovery.last_failure == _refused(T0)
    assert discovery.current_failure == _refused(T0)


def test_a_catalog_discovery_holds_a_scan_or_a_failure():
    """A record with neither a scan time nor a failure says nothing and is refused."""
    with pytest.raises(InvariantViolation):
        CatalogDiscovery(id=CatalogDiscoveryId("iceberg"))


def test_a_scanned_catalog_has_no_current_failure():
    """A catalog only ever scanned has no failure."""
    assert CatalogDiscovery.first("iceberg", T0).current_failure is None


def test_a_failure_after_the_last_scan_is_current():
    """A failure newer than the last completed scan is the catalog's current state."""
    discovery = CatalogDiscovery.first("iceberg", T0)
    discovery.record_failure(_refused(T1))
    assert discovery.current_failure == _refused(T1)
    assert discovery.last_discovered_at == T0


def test_a_failure_before_the_last_scan_is_not_current():
    """A failure recorded late, from a scan older than the last completed one, is not current."""
    discovery = CatalogDiscovery.first("iceberg", T1)
    discovery.record_failure(_refused(T0))
    assert discovery.last_failure == _refused(T0)
    assert discovery.current_failure is None


def test_a_failure_at_the_same_time_as_the_last_scan_is_not_current():
    """A failure is current only while strictly newer than the last completed scan; the same time is not."""
    discovery = CatalogDiscovery.first("iceberg", T0)
    discovery.record_failure(_refused(T0))
    assert discovery.last_failure == _refused(T0)
    assert discovery.current_failure is None


def test_a_scan_after_the_failure_makes_it_not_current_without_deleting_it():
    """A later completed scan clears the current failure; the failure itself is kept."""
    discovery = CatalogDiscovery.failed("iceberg", _refused(T0))
    discovery.record(T1)
    assert discovery.last_discovered_at == T1
    assert discovery.current_failure is None
    assert discovery.last_failure == _refused(T0)


def test_an_older_failure_does_not_replace_a_newer_one():
    """A failure from a scan that started earlier never replaces the recorded one."""
    discovery = CatalogDiscovery.failed("iceberg", _missing(T1))
    discovery.record_failure(_refused(T0))
    assert discovery.last_failure == _missing(T1)


def test_a_newer_failure_replaces_the_older_one():
    """Each later failure is recorded, its reason with it."""
    discovery = CatalogDiscovery.failed("iceberg", _refused(T0))
    discovery.record_failure(_missing(T1))
    assert discovery.last_failure == _missing(T1)
