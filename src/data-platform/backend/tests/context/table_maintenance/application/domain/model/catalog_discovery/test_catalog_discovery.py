"""Test the CatalogDiscovery aggregate: when discovery last scanned a whole catalog."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogDiscovery,
    CatalogDiscoveryId,
)

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
    with pytest.raises(ValidationError):
        CatalogDiscovery.first("", T0)
