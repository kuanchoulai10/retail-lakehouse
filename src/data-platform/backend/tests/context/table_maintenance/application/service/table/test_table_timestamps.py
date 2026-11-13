"""Test when the services move a table's last commit and last discovery, and how they are listed."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogDiscovery,
    CatalogDiscoveryId,
)
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    GlobList,
    RuleAction,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.port.inbound.table import (
    GetTableUseCaseInput,
    ListTablesUseCaseInput,
    PlanTableMaintenanceUseCaseInput,
    ProcessTableHintUseCaseInput,
    SyncDiscoveredTablesUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    CatalogNotFoundError,
    TableMetadataObservation,
)
from context.table_maintenance.application.service.table import (
    GetTableService,
    ListTablesService,
    ProcessTableHintService,
    SyncDiscoveredTablesService,
)
from tests.context.table_maintenance.fakes.plan_service_on_fakes import plan_service_on_fakes
from tests.context.table_maintenance.fakes.track_calls import track_calls

EARLIER = datetime(2026, 10, 24, 11, 0, tzinfo=UTC)
COMMIT = datetime(2026, 10, 24, 11, 30, tzinfo=UTC)
NEWER_COMMIT = COMMIT + timedelta(minutes=5)
NAME = TableName(catalog="iceberg", namespace="sales", table="orders")


def _include_all(rules_repo, now):
    every = GlobList(globs=("*",))
    rule = TableDiscoveryRule.create(
        id=TableDiscoveryRuleId("r-1"),
        priority=10,
        action=RuleAction.INCLUDE,
        enabled=True,
        catalogs=every,
        namespaces=every,
        tables=every,
        now=now,
    )
    rules = rules_repo.get_rules()
    rules.replace((rule,), rules.version, now, new_ids={rule.id})
    rules_repo.save(rules)


def _row(repo, at, uuid="u-1", name=NAME):
    table = Table.register(TableId(uuid), name, TableDiscoveryRuleId("r-1"), at)
    repo.create(table)
    return table


@pytest.fixture
def sync(tables_repo, rules_repo, discoveries_repo, catalog, signals, clock):
    """Provide the sync discovered tables service on the fakes."""
    return SyncDiscoveredTablesService(tables_repo, rules_repo, discoveries_repo, catalog, signals, clock=clock)


@pytest.fixture
def hint(tables_repo, rules_repo, catalog, signals, discovery_requests, clock):
    """Provide the process table hint service on the fakes."""
    return ProcessTableHintService(tables_repo, rules_repo, catalog, signals, discovery_requests, clock=clock)


def _catalog_wide():
    return SyncDiscoveredTablesUseCaseInput(catalog="iceberg")


# --- last discovered: discovery records each catalog-wide scan ---


def test_a_catalog_wide_sync_records_when_it_scanned_the_catalog(sync, discoveries_repo, now):
    """A catalog-wide sync records its catalog's discovery at the time it started."""
    sync.execute(_catalog_wide())
    assert discoveries_repo.get(CatalogDiscoveryId("iceberg")).last_discovered_at == now


def test_a_later_catalog_wide_sync_moves_the_catalogs_discovery(sync, discoveries_repo, now):
    """Each catalog-wide sync moves its catalog's discovery forward."""
    discoveries_repo.save(CatalogDiscovery.first("iceberg", EARLIER))
    sync.execute(_catalog_wide())
    assert discoveries_repo.get(CatalogDiscoveryId("iceberg")).last_discovered_at == now


def test_a_namespace_sync_records_no_discovery(sync, discoveries_repo):
    """A namespace sync does not see the whole catalog, so it records nothing."""
    sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace="sales"))
    assert discoveries_repo.list_all() == []


def test_a_failed_sync_records_no_discovery(sync, discoveries_repo, catalog, monkeypatch):
    """A sync that cannot list the catalog saw nothing, so it records nothing."""

    def unknown(_input):
        raise CatalogNotFoundError("iceberg")

    monkeypatch.setattr(catalog, "list_tables", unknown)
    with pytest.raises(CatalogNotFoundError):
        sync.execute(_catalog_wide())
    assert discoveries_repo.list_all() == []


def test_a_sync_does_not_save_tables_only_because_it_saw_them(sync, tables_repo, rules_repo, catalog, log, now):
    """Seeing an unchanged table writes nothing for it: its catalog's discovery stands for it."""
    _include_all(rules_repo, now)
    _row(tables_repo, EARLIER)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    sync.execute(_catalog_wide())
    assert log == []


def test_a_table_dropped_by_a_sync_keeps_the_previous_discovery(sync, tables_repo, discoveries_repo, now):
    """A table missing from this scan was last seen by the scan before it."""
    _row(tables_repo, EARLIER - timedelta(days=1))
    discoveries_repo.save(CatalogDiscovery.first("iceberg", EARLIER))
    sync.execute(_catalog_wide())
    assert tables_repo.get(TableId("u-1")).last_discovered_at == EARLIER
    assert discoveries_repo.get(CatalogDiscoveryId("iceberg")).last_discovered_at == now


# --- last commit: taken from the catalog wherever the backend reads the table ---


def test_a_sync_registers_a_table_with_its_last_commit(sync, tables_repo, catalog):
    """A newly discovered table starts with the catalog's newest commit."""
    catalog.add_table("iceberg", "sales", "orders", "u-1", last_committed_at=COMMIT.isoformat())
    sync.execute(_catalog_wide())
    assert tables_repo.get(TableId("u-1")).last_committed_at == COMMIT


def test_a_sync_registers_a_table_never_committed_to_without_a_last_commit(sync, tables_repo, catalog):
    """A table without snapshots has no last commit."""
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    assert tables_repo.get(TableId("u-1")).last_committed_at is None


def test_a_sync_saves_a_newer_commit_of_a_known_table(sync, tables_repo, rules_repo, catalog, log, now):
    """A known table whose newest commit moved is saved once, with the new time."""
    _include_all(rules_repo, now)
    _row(tables_repo, EARLIER).record_last_commit(COMMIT)
    catalog.add_table("iceberg", "sales", "orders", "u-1", last_committed_at=NEWER_COMMIT.isoformat())
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    sync.execute(_catalog_wide())
    assert log == [("tables.update", "u-1")]
    assert tables_repo.get(TableId("u-1")).last_committed_at == NEWER_COMMIT


def test_a_sync_never_moves_a_last_commit_back(sync, tables_repo, rules_repo, catalog, log, now):
    """An older commit time read from the catalog changes and saves nothing."""
    _include_all(rules_repo, now)
    _row(tables_repo, EARLIER).record_last_commit(NEWER_COMMIT)
    catalog.add_table("iceberg", "sales", "orders", "u-1", last_committed_at=COMMIT.isoformat())
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    sync.execute(_catalog_wide())
    assert log == []
    assert tables_repo.get(TableId("u-1")).last_committed_at == NEWER_COMMIT


def test_a_catalog_event_saves_the_newer_commit_of_a_known_table(hint, tables_repo, rules_repo, catalog, now):
    """A table update event reads the table from the catalog and saves its newest commit."""
    _include_all(rules_repo, now)
    _row(tables_repo, EARLIER).record_last_commit(COMMIT)
    catalog.add_table("iceberg", "sales", "orders", "u-1", last_committed_at=NEWER_COMMIT.isoformat())
    hint.execute(ProcessTableHintUseCaseInput("iceberg", "sales", "orders", "AFTER_UPDATE_TABLE"))
    assert tables_repo.get(TableId("u-1")).last_committed_at == NEWER_COMMIT


def test_a_catalog_event_saves_the_newer_commit_of_an_unmanaged_table(hint, tables_repo, catalog, log):
    """An unmanaged table, which is never reconciled, still gets its last commit from events."""
    table = _row(tables_repo, EARLIER)
    table.unmanage(EARLIER)
    catalog.add_table("iceberg", "sales", "orders", "u-1", last_committed_at=COMMIT.isoformat())
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    hint.execute(ProcessTableHintUseCaseInput("iceberg", "sales", "orders", "AFTER_UPDATE_TABLE"))
    assert log == [("tables.update", "u-1")]
    assert tables_repo.get(TableId("u-1")).last_committed_at == COMMIT


def test_a_catalog_event_registers_a_table_with_its_last_commit(hint, tables_repo, catalog):
    """A table first seen through an event starts with its newest commit."""
    catalog.add_table("iceberg", "sales", "orders", "u-1", last_committed_at=COMMIT.isoformat())
    hint.execute(ProcessTableHintUseCaseInput("iceberg", "sales", "orders", "AFTER_CREATE_TABLE"))
    assert tables_repo.get(TableId("u-1")).last_committed_at == COMMIT


def _observation(*commits: datetime) -> TableMetadataObservation:
    return TableMetadataObservation(
        table_uuid="u-1",
        snapshots=[{"snapshot_id": i, "committed_at": c.isoformat()} for i, c in enumerate(commits, start=1)],
    )


def test_a_reconcile_saves_the_newest_commit_it_observes(tables_repo, catalog, resolve_applicable_policy, log, now):
    """Reconciling a table observes its snapshots and saves the newest commit time."""
    _row(tables_repo, EARLIER).record_last_commit(COMMIT)
    catalog.observations[("iceberg", "sales", "orders")] = _observation(COMMIT, NEWER_COMMIT)
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    plan_service_on_fakes(tables_repo, catalog, resolve_applicable_policy).execute(
        PlanTableMaintenanceUseCaseInput(table_uuid="u-1", now=now)
    )
    assert log == [("tables.update", "u-1")]
    assert tables_repo.get(TableId("u-1")).last_committed_at == NEWER_COMMIT


def test_a_reconcile_that_observes_no_newer_commit_saves_nothing(
    tables_repo, catalog, resolve_applicable_policy, log, now
):
    """An observation whose newest commit is already known writes nothing."""
    _row(tables_repo, EARLIER).record_last_commit(NEWER_COMMIT)
    catalog.observations[("iceberg", "sales", "orders")] = _observation(COMMIT, NEWER_COMMIT)
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    plan_service_on_fakes(tables_repo, catalog, resolve_applicable_policy).execute(
        PlanTableMaintenanceUseCaseInput(table_uuid="u-1", now=now)
    )
    assert log == []


# --- listing ---


def test_listing_shows_the_last_commit_and_the_last_discovery(tables_repo, discoveries_repo):
    """A live table shows its catalog's discovery, a dropped one its stamp, an undiscovered catalog's none."""
    _row(tables_repo, EARLIER - timedelta(days=1), "u-live").record_last_commit(COMMIT)
    gone = TableName(catalog="iceberg", namespace="sales", table="gone")
    dropped = _row(tables_repo, EARLIER - timedelta(days=1), "u-gone", gone)
    dropped.mark_dropped(EARLIER, catalog_discovered_at=EARLIER - timedelta(hours=1))
    _row(tables_repo, EARLIER, "u-other", TableName(catalog="other", namespace="sales", table="orders"))
    discoveries_repo.save(CatalogDiscovery.first("iceberg", EARLIER))
    listed = ListTablesService(tables_repo, discoveries_repo).execute(ListTablesUseCaseInput())
    items = {i.uuid: i for i in listed.items}
    assert (items["u-live"].last_committed_at, items["u-live"].last_discovered_at) == (COMMIT, EARLIER)
    assert (items["u-gone"].last_committed_at, items["u-gone"].last_discovered_at) == (
        None,
        EARLIER - timedelta(hours=1),
    )
    assert (items["u-other"].last_committed_at, items["u-other"].last_discovered_at) == (None, None)


def test_getting_a_table_shows_the_last_commit_and_the_last_discovery(tables_repo, discoveries_repo):
    """One table shows the same two times as the listing."""
    _row(tables_repo, EARLIER - timedelta(days=1)).record_last_commit(COMMIT)
    discoveries_repo.save(CatalogDiscovery.first("iceberg", EARLIER))
    out = GetTableService(tables_repo, discoveries_repo).execute(GetTableUseCaseInput(uuid="u-1"))
    assert (out.last_committed_at, out.last_discovered_at) == (COMMIT, EARLIER)
