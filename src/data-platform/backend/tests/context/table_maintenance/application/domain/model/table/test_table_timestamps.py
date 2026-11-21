"""Test the Table aggregate's last commit and last discovered times."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
)
from tests.context.table_maintenance.discovery_decision_samples import MANAGED, UNMANAGED

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)
NAME = TableName(catalog="iceberg", namespace="inventory", table="orders")


def managed(at: datetime = T0) -> Table:
    """Provide a table registered as managed at ``at``."""
    return Table.register(TableId("u1"), NAME, MANAGED, at)


# --- last commit ---


def test_a_new_table_has_no_known_last_commit():
    """Until a commit is seen, the last commit is unknown."""
    assert managed().last_committed_at is None
    assert Table.register(TableId("u1"), NAME, UNMANAGED, T0).last_committed_at is None


def test_recording_a_commit_sets_the_last_commit_and_leaves_updated_at():
    """The last commit is an observation of the catalog, not a change of maintenance state."""
    t = managed()
    assert t.record_last_commit(T1) is True
    assert t.last_committed_at == T1
    assert t.updated_at == T0


def test_the_last_commit_only_moves_forward():
    """An older or equal commit time, or none, changes nothing."""
    t = managed()
    t.record_last_commit(T2)
    assert t.record_last_commit(T1) is False
    assert t.record_last_commit(T2) is False
    assert t.record_last_commit(None) is False
    assert t.last_committed_at == T2


def test_a_dropped_table_keeps_its_last_commit():
    """A dropped table is gone from the catalog, so nothing moves its last commit."""
    t = managed()
    t.record_last_commit(T1)
    t.mark_dropped(T1)
    assert t.record_last_commit(T2) is False
    assert t.last_committed_at == T1


# --- last discovered ---


def test_a_live_table_is_last_discovered_at_its_catalogs_last_discovery():
    """A live table was seen by its catalog's last discovery."""
    t = managed(T0)
    assert t.last_discovered(T1) == T1
    assert t.last_discovered_at is None


def test_a_live_table_registered_after_the_last_discovery_was_last_seen_registering():
    """A table registered (by a catalog event) after its catalog's last discovery was last seen when registered."""
    t = managed(T2)
    assert t.last_discovered(T1) == T2


def test_a_live_table_of_a_never_discovered_catalog_has_no_known_last_discovery():
    """Without a discovery of its catalog, the last discovery is unknown."""
    assert managed().last_discovered(None) is None


def test_dropping_a_table_stamps_when_it_was_last_seen():
    """A dropped table keeps the time it was last seen, whatever its catalog's discoveries do next."""
    t = managed(T0)
    t.mark_dropped(T2, catalog_discovered_at=T1)
    assert t.last_discovered_at == T1
    assert t.last_discovered(T2) == T1
    assert t.last_discovered(None) == T1


def test_dropping_a_table_registered_after_the_last_discovery_stamps_its_registration():
    """A table registered after the last discovery and gone by the next was last seen when registered."""
    t = managed(T1)
    t.mark_dropped(T2, catalog_discovered_at=T0)
    assert t.last_discovered_at == T1


def test_dropping_a_table_of_a_never_discovered_catalog_stamps_nothing():
    """Without a discovery of its catalog, when the table was last seen is unknown."""
    t = managed(T0)
    t.mark_dropped(T2)
    assert t.last_discovered_at is None
    assert t.last_discovered(T2) is None


def test_dropping_an_already_dropped_table_keeps_its_stamp():
    """Dropping is idempotent: the first stamp stays."""
    t = managed(T0)
    t.mark_dropped(T1, catalog_discovered_at=T0)
    t.mark_dropped(T2, catalog_discovered_at=T1)
    assert t.last_discovered_at == T0
