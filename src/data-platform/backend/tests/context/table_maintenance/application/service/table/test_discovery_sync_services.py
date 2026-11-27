"""Test the discovery sync and table hint services: each table's nearest discovery policy decides it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.application.domain.model.catalog_discovery import (
    CatalogScanFailure,
    CatalogScanFailureReason,
)
from context.table_maintenance.application.domain.model.shared import (
    CatalogDiscoveryId,
    ComputeSize,
    MaintenanceOperation,
    TableId,
)
from context.table_maintenance.application.domain.model.table import Table, TableName, TableStatus
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DecidedBy,
    ManagementDecision,
    TableDiscoveryPolicy,
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.domain.model.table_discovery_policy_attachment import (
    TableDiscoveryPolicyAttachment,
)
from context.table_maintenance.application.domain.service.table_discovery_policy_attachment import scanned_catalogs
from context.table_maintenance.application.exceptions import ConcurrentUpdateError, ConflictError
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCaseInput,
    ProcessTableHintUseCaseInput,
    SyncDiscoveredTablesUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import TableMetadataObservation
from context.table_maintenance.application.service.table import (
    ProcessTableHintService,
    SyncDiscoveredTablesService,
)
from tests.context.table_maintenance.application.domain.service.table_discovery_policy_attachment.discovery_policy_samples import (  # noqa: E501
    MANAGE_ALL,
    NOW,
    UNMANAGE_ALL,
    catalog_target,
    namespace_target,
    rules,
    table_target,
)
from tests.context.table_maintenance.fakes.plan_service_on_fakes import plan_service_on_fakes
from tests.context.table_maintenance.fakes.track_calls import track_calls

if TYPE_CHECKING:
    from tests.context.table_maintenance.fakes.fake_read_table_metadata_gateway import FakeReadTableMetadataGateway
    from tests.context.table_maintenance.fakes.in_memory_catalog_discoveries_repo import InMemoryCatalogDiscoveriesRepo
    from tests.context.table_maintenance.fakes.in_memory_table_discovery_policies_repo import (
        InMemoryTableDiscoveryPoliciesRepo,
    )
    from tests.context.table_maintenance.fakes.in_memory_table_discovery_policy_attachments_repo import (
        InMemoryTableDiscoveryPolicyAttachmentsRepo,
    )
    from tests.context.table_maintenance.fakes.in_memory_tables_repo import InMemoryTablesRepo

MANAGE_RULE = 1
REST_RULE = 1
TMP_RULE = 2


def _policy(name: str, *specs: tuple[str, str]) -> TableDiscoveryPolicy:
    """Return a policy of ``(action, table name pattern)`` rules, in order."""
    return TableDiscoveryPolicy.create(TableDiscoveryPolicyName(value=name), "", rules(*specs), NOW)


ALL_BUT_TMP = _policy("all-but-tmp", ("include", "*"), ("exclude", "tmp_*"))
ONLY_BACK = _policy("only-back", ("include", "back"))


def _position(table: Table) -> int | None:
    """Return the position of the rule that decided the table, None when no rule or no policy did."""
    return None if table.decided_by is None else table.decided_by.rule_position


@dataclass
class _World:
    """Hold the fakes a scan reads, and attach policies the way the attach service stores them."""

    tables: InMemoryTablesRepo
    policies: InMemoryTableDiscoveryPoliciesRepo
    attachments: InMemoryTableDiscoveryPolicyAttachmentsRepo
    catalog: FakeReadTableMetadataGateway
    discoveries: InMemoryCatalogDiscoveriesRepo

    def attach(self, target, policy):
        """Store the policy if it is new, and attach it to the target, replacing what the target held."""
        if self.policies.get(policy.id) is None:
            self.policies.create(policy)
        existing = self.attachments.get_by_target(target)
        if existing is None:
            self.attachments.create(TableDiscoveryPolicyAttachment.attach(target, policy.id, NOW))
        else:
            existing.replace_policy(policy.id, NOW)
            self.attachments.update(existing)

    def attach_to_catalog(self, policy):
        """Attach the policy to the catalog ``iceberg``."""
        self.attach(catalog_target("iceberg"), policy)

    def next_version(self, policy):
        """Store the next version of the policy with the same description and rules."""
        stored = self.policies.get(policy.id)
        assert stored is not None
        stored.revise(stored.description, stored.rules, stored.version, NOW)
        self.policies.update(stored)


@pytest.fixture
def world(tables_repo, discovery_policies, discovery_attachments, catalog, discoveries_repo):
    """Provide the fakes a scan reads, with nothing attached and no catalog discovered yet."""
    return _World(tables_repo, discovery_policies, discovery_attachments, catalog, discoveries_repo)


def _row(repo, now, uuid, name, *, by: TableDiscoveryPolicy | None = MANAGE_ALL):
    """Store a table as the policy ``by`` at version 1 decides it, or as nothing attached decides it for None."""
    decision = ManagementDecision.nothing_attached() if by is None else by.should_manage(name)
    table = Table.register(TableId(uuid), name, decision, now)
    repo.create(table)
    return table


def _name(table, namespace="sales"):
    return TableName(catalog="iceberg", namespace=namespace, table=table)


@pytest.fixture
def sync(tables_repo, discovery_policies, discovery_attachments, discoveries_repo, catalog, signals, clock):
    """Provide the sync discovered tables service on the fakes."""
    return SyncDiscoveredTablesService(
        tables_repo,
        discovery_policies,
        discovery_attachments,
        discoveries_repo,
        catalog,
        signals,
        clock=clock,
    )


def _calls(signals):
    return [(c.table_uuid, c.change, c.is_managed) for c in signals.calls]


def _catalog_wide():
    return SyncDiscoveredTablesUseCaseInput(catalog="iceberg")


def _namespace(namespace="sales"):
    return SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace=namespace)


# --- sync: the nearest discovery policy decides ---


def test_a_namespace_policy_manages_its_tables_under_the_deciding_rule(sync, world, signals):
    """A policy attached to a namespace manages its tables and records the policy, version and rule."""
    world.attach(namespace_target("iceberg", "sales"), MANAGE_ALL)
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    world.catalog.add_table("iceberg", "hr", "people", "u-2")
    sync.execute(_catalog_wide())
    managed = world.tables.get(TableId("u-1"))
    assert managed.is_managed
    assert managed.decided_by == DecidedBy(policy_id=MANAGE_ALL.id, policy_version=1, rule_position=MANAGE_RULE)
    assert not world.tables.get(TableId("u-2")).is_managed
    assert _calls(signals) == [("u-1", "managed", True)]


def test_a_table_policy_overrides_its_namespace(sync, world, signals):
    """An excluding policy attached to a table opts it out of the managing policy of its namespace."""
    world.attach(namespace_target("iceberg", "sales"), MANAGE_ALL)
    world.attach(table_target(_name("orders"), "u-1"), UNMANAGE_ALL)
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    world.catalog.add_table("iceberg", "sales", "items", "u-2")
    sync.execute(_catalog_wide())
    opted_out = world.tables.get(TableId("u-1"))
    assert not opted_out.is_managed
    assert opted_out.decided_by == DecidedBy(policy_id=UNMANAGE_ALL.id, policy_version=1, rule_position=1)
    assert world.tables.get(TableId("u-2")).is_managed
    assert _calls(signals) == [("u-2", "managed", True)]


def test_nothing_attached_registers_unmanaged_and_sends_nothing(sync, world, signals):
    """With nothing attached nothing decides: the table is unmanaged and names no policy."""
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_catalog_wide())
    table = world.tables.get(TableId("u-1"))
    assert (out.registered, table.status) == (1, TableStatus.UNMANAGED)
    assert table.decided_by is None
    assert signals.calls == []


def test_a_table_no_rule_matches_is_unmanaged_by_its_policy_with_no_rule(sync, world, signals):
    """A table none of its policy's rules match is unmanaged, decided by that policy with no rule position."""
    world.attach_to_catalog(ONLY_BACK)
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    table = world.tables.get(TableId("u-1"))
    assert not table.is_managed
    assert table.decided_by == DecidedBy(policy_id=ONLY_BACK.id, policy_version=1, rule_position=None)
    assert signals.calls == []


def test_a_managed_table_now_excluded_is_stopped(sync, tables_repo, world, signals, now):
    """A managed table whose policy now excludes it is saved unmanaged under the excluding rule and sent ``stopped``."""
    world.attach_to_catalog(ALL_BUT_TMP)
    _row(tables_repo, now, "u-1", _name("tmp_orders"))
    world.catalog.add_table("iceberg", "sales", "tmp_orders", "u-1")
    out = sync.execute(_catalog_wide())
    table = world.tables.get(TableId("u-1"))
    assert table.status == TableStatus.UNMANAGED
    assert table.decided_by == DecidedBy(policy_id=ALL_BUT_TMP.id, policy_version=1, rule_position=TMP_RULE)
    assert out.unmanaged == 1
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_a_table_moved_out_of_a_managing_namespace_is_decided_by_its_new_name(sync, world, tables_repo, signals, now):
    """A scan decides a known table by the name the catalog gives it now, not the name stored for it."""
    world.attach(namespace_target("iceberg", "sales"), MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    world.catalog.add_table("iceberg", "other", "orders", "u-1")
    out = sync.execute(_catalog_wide())
    table = world.tables.get(TableId("u-1"))
    assert (table.name.namespace, table.status) == ("other", TableStatus.UNMANAGED)
    assert table.decided_by is None
    assert (out.renamed, out.unmanaged) == (1, 1)
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_a_renamed_table_keeps_its_table_attachment(sync, world, tables_repo, now):
    """A table attached by uuid keeps its own policy after a rename to another namespace."""
    old_name = _name("orders")
    _row(tables_repo, now, "u1", old_name)
    world.catalog.add_table("iceberg", "sales", "orders", "u1")
    world.attach(table_target(old_name, "u1"), MANAGE_ALL)
    world.catalog.rename("u1", namespace="other")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace=None))
    assert world.tables.get(TableId("u1")).is_managed
    assert out.renamed == 1
    assert world.tables.get(TableId("u1")).name.namespace == "other"


def test_a_new_policy_version_moves_the_decision_and_sends_nothing(sync, world, tables_repo, signals, log, now):
    """On a namespace scan a new version of the deciding policy is a decision change: the row is saved, nothing sent.

    A catalog-wide scan still sends ``seen`` to the managed table, as
    ``test_managed_table_now_decided_by_another_managing_policy_records_it`` pins.
    """
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    world.next_version(MANAGE_ALL)
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    out = sync.execute(_namespace())
    table = world.tables.get(TableId("u-1"))
    assert table.is_managed
    assert table.decided_by == DecidedBy(policy_id=MANAGE_ALL.id, policy_version=2, rule_position=MANAGE_RULE)
    assert (out.managed, out.unmanaged) == (0, 0)
    assert log == [("tables.update", "u-1")]
    assert signals.calls == []


def test_the_scan_reads_attachments_once_per_catalog(sync, world, log):
    """A scan reads its catalog's attachments in one call, and their policies in one more, however many tables."""
    world.attach(namespace_target("iceberg", "sales"), MANAGE_ALL)
    world.attach(namespace_target("iceberg", "hr"), UNMANAGE_ALL)
    for uuid, namespace, table in (("u-1", "sales", "a"), ("u-2", "sales", "b"), ("u-3", "hr", "c")):
        world.catalog.add_table("iceberg", namespace, table, uuid)
    track_calls(world.attachments, "list_in_catalog", "attachments.list_in_catalog", log, str)
    track_calls(world.attachments, "get_many_by_targets", "attachments.get_many_by_targets", log, str)
    track_calls(world.policies, "get_many", "policies.get_many", log, lambda ids: str(len(ids)))
    sync.execute(_catalog_wide())
    assert log == [("attachments.list_in_catalog", "iceberg"), ("policies.get_many", "2")]


# --- sync: a catalog or a table the scan cannot read ---


def test_a_refused_catalog_is_recorded_and_changes_nothing(sync, world, signals, now):
    """A catalog that refuses the credential records ``cannot_access`` at the scan's start and changes no table."""
    world.attach(catalog_target("iceberg"), MANAGE_ALL)
    _row(world.tables, now, "u-1", _name("kept"))
    world.catalog.deny("iceberg")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace=None))
    assert out.failure == "cannot_access"
    assert (out.registered, out.renamed, out.dropped, out.skipped, out.ensured) == (0, 0, 0, 0, 0)
    failure = world.discoveries.get(CatalogDiscoveryId("iceberg")).current_failure
    assert failure == CatalogScanFailure(
        reason=CatalogScanFailureReason.CANNOT_ACCESS,
        detail="the platform's catalog credential cannot read catalog iceberg",
        failed_at=now,
    )
    assert world.discoveries.get(CatalogDiscoveryId("iceberg")).last_discovered_at is None
    assert world.tables.get(TableId("u-1")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_a_refused_namespace_scan_is_recorded_on_its_catalog(sync, world, now):
    """A namespace scan of a refused catalog records the failure on the catalog too."""
    world.catalog.deny("iceberg")
    out = sync.execute(_namespace())
    assert out.failure == "cannot_access"
    failure = world.discoveries.get(CatalogDiscoveryId("iceberg")).current_failure
    assert failure.reason is CatalogScanFailureReason.CANNOT_ACCESS


def test_a_later_good_scan_makes_the_failure_not_current(
    world, discovery_policies, discovery_attachments, signals, now
):
    """Once the catalog is readable again, the next completed scan clears the current failure and keeps it."""
    times = iter((now, now + timedelta(minutes=5)))
    sync = SyncDiscoveredTablesService(
        world.tables,
        discovery_policies,
        discovery_attachments,
        world.discoveries,
        world.catalog,
        signals,
        clock=lambda: next(times),
    )
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    world.catalog.deny("iceberg")
    sync.execute(_catalog_wide())
    world.catalog.allow("iceberg")
    out = sync.execute(_catalog_wide())
    discovery = world.discoveries.get(CatalogDiscoveryId("iceberg"))
    assert out.failure is None
    assert out.registered == 1
    assert discovery.current_failure is None
    assert discovery.last_failure is not None


def test_a_missing_catalog_is_recorded_not_found(sync, world, signals, now):
    """A catalog that no longer exists records ``not_found`` and drops nothing; it never reads as every table gone."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(world.tables, now, "u-1", _name("kept"))
    world.catalog.drop_catalog("iceberg")
    out = sync.execute(_catalog_wide())
    assert out.failure == "not_found"
    assert out.dropped == 0
    failure = world.discoveries.get(CatalogDiscoveryId("iceberg")).current_failure
    assert failure == CatalogScanFailure(
        reason=CatalogScanFailureReason.NOT_FOUND, detail="catalog iceberg not found", failed_at=now
    )
    assert world.tables.get(TableId("u-1")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_a_refused_catalog_with_nothing_attached_unmanages_its_managed_tables(sync, world, signals, now):
    """Unread, a catalog with no policy attached in it still unmanages its stored managed tables, each sent stopped."""
    world.attach(catalog_target("lake"), MANAGE_ALL)
    _row(world.tables, now, "u-1", _name("orders"))
    _row(world.tables, now, "u-2", _name("items", namespace="hr"))
    elsewhere = TableName(catalog="lake", namespace="sales", table="orders")
    _row(world.tables, now, "u-lake", elsewhere)
    world.catalog.deny("iceberg")

    out = sync.execute(_catalog_wide())

    assert out.failure == "cannot_access"
    assert out.unmanaged == 2
    for uuid in ("u-1", "u-2"):
        table = world.tables.get(TableId(uuid))
        assert table.status == TableStatus.UNMANAGED
        assert table.decided_by is None
    assert world.tables.get(TableId("u-lake")).status == TableStatus.MANAGED
    assert sorted(_calls(signals)) == [("u-1", "stopped", False), ("u-2", "stopped", False)]


def test_a_missing_catalog_with_nothing_attached_unmanages_its_managed_tables(sync, world, signals, now):
    """A catalog that is gone and has nothing attached manages nothing: its managed tables are unmanaged."""
    _row(world.tables, now, "u-1", _name("orders"))
    world.catalog.drop_catalog("iceberg")

    out = sync.execute(_catalog_wide())

    assert (out.failure, out.unmanaged, out.dropped) == ("not_found", 1, 0)
    table = world.tables.get(TableId("u-1"))
    assert table.status == TableStatus.UNMANAGED
    assert table.decided_by is None
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_a_namespace_policy_keeps_its_unread_catalog_scanned(sync, world, signals, now):
    """A policy attached under the catalog keeps it scanned, so an unread scan changes no table."""
    world.attach(namespace_target("iceberg", "hr"), MANAGE_ALL)
    _row(world.tables, now, "u-1", _name("orders"))
    world.catalog.deny("iceberg")

    out = sync.execute(_catalog_wide())

    assert (out.failure, out.unmanaged) == ("cannot_access", 0)
    assert world.tables.get(TableId("u-1")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_an_exclude_only_policy_keeps_its_unread_catalog_scanned_and_retires_its_managed_tables(
    sync, world, signals, now
):
    """A catalog whose only policy cannot include stays scanned, yet its managed tables are unmanaged unread.

    No table there can end up managed, so the stored managed table is unmanaged from its row, decided by
    the exclude-only policy's rule, and sent ``stopped``.
    """
    world.attach_to_catalog(UNMANAGE_ALL)
    _row(world.tables, now, "u-1", _name("orders"))
    world.catalog.deny("iceberg")

    out = sync.execute(_catalog_wide())

    policies = {p.id: p for p in world.policies.list_all()}
    assert scanned_catalogs(world.attachments.list_all(), policies) == ("iceberg",)
    assert (out.failure, out.unmanaged) == ("cannot_access", 1)
    table = world.tables.get(TableId("u-1"))
    assert table.status == TableStatus.UNMANAGED
    assert table.decided_by == DecidedBy(policy_id=UNMANAGE_ALL.id, policy_version=1, rule_position=1)
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_a_catalog_with_nothing_attached_unmanages_a_managed_table_it_cannot_load(sync, world, signals, now):
    """A managed table the scan cannot load is unmanaged from its stored row, as the tables it lists are."""
    _row(world.tables, now, "u-listed", _name("orders"))
    world.catalog.add_table("iceberg", "sales", "orders", "u-listed")
    world.catalog.add_table("iceberg", "sales", "secret", "u-refused")
    world.catalog.deny_table("iceberg", "sales", "secret")
    _row(world.tables, now, "u-refused", _name("secret"))

    out = sync.execute(_catalog_wide())

    assert out.unmanaged == 2
    assert world.tables.get(TableId("u-refused")).status == TableStatus.UNMANAGED
    assert sorted(_calls(signals)) == [("u-listed", "stopped", False), ("u-refused", "stopped", False)]


def test_a_fully_read_catalog_with_nothing_attached_drops_a_missing_managed_table_without_unmanaging_it(
    sync, world, signals, now
):
    """A managed table missing from a fully read catalog that is no longer scanned is dropped, not unmanaged first."""
    gone = _row(world.tables, now, "u-gone", _name("gone"))
    decided_by = gone.decided_by

    out = sync.execute(_catalog_wide())

    assert (out.dropped, out.unmanaged) == (1, 0)
    table = world.tables.get(TableId("u-gone"))
    assert table.status == TableStatus.DROPPED
    assert table.decided_by == decided_by
    assert _calls(signals) == [("u-gone", "stopped", False)]


def test_a_namespace_scan_of_a_catalog_with_nothing_attached_decides_only_what_it_lists(sync, world, signals, now):
    """Only a catalog-wide scan unmanages from the stored rows; a namespace scan still decides only what it lists."""
    _row(world.tables, now, "u-1", _name("orders"))
    world.catalog.deny("iceberg")

    out = sync.execute(_namespace())

    assert (out.failure, out.unmanaged) == ("cannot_access", 0)
    assert world.tables.get(TableId("u-1")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_a_refused_table_is_skipped_and_nothing_is_dropped(sync, world, signals, now):
    """A table the credential cannot load is skipped, and that scan drops no table, the refused one or any other."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(world.tables, now, "u-refused", _name("secret"))
    _row(world.tables, now, "u-gone", _name("gone"))
    world.catalog.add_table("iceberg", "sales", "secret", "u-refused")
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    world.catalog.deny_table("iceberg", "sales", "secret")
    out = sync.execute(_catalog_wide())
    assert out.failure is None
    assert (out.registered, out.skipped, out.dropped) == (1, 1, 0)
    assert world.tables.get(TableId("u-refused")).status == TableStatus.MANAGED
    assert world.tables.get(TableId("u-gone")).status == TableStatus.MANAGED
    assert ("u-gone", "stopped", False) not in _calls(signals)


def test_a_scan_after_the_refused_table_is_readable_drops_again(sync, world, now):
    """The drop pass is off only for the scan that met a refused table."""
    _row(world.tables, now, "u-gone", _name("gone"))
    world.catalog.add_table("iceberg", "sales", "secret", "u-refused")
    world.catalog.deny_table("iceberg", "sales", "secret")
    sync.execute(_catalog_wide())
    world.catalog.denied_tables.clear()
    out = sync.execute(_catalog_wide())
    assert out.dropped == 1
    assert world.tables.get(TableId("u-gone")).status == TableStatus.DROPPED


def test_a_scan_with_an_unreadable_table_still_counts_as_a_scan(
    world, discovery_policies, discovery_attachments, signals, now
):
    """A catalog readable again but for one table: the scan records its time, clears the failure and drops nothing."""
    times = iter((now - timedelta(minutes=5), now))
    sync = SyncDiscoveredTablesService(
        world.tables,
        discovery_policies,
        discovery_attachments,
        world.discoveries,
        world.catalog,
        signals,
        clock=lambda: next(times),
    )
    _row(world.tables, now, "u-gone", _name("gone"))
    world.catalog.add_table("iceberg", "sales", "secret", "u-refused")
    world.catalog.deny("iceberg")
    sync.execute(_catalog_wide())
    world.catalog.allow("iceberg")
    world.catalog.deny_table("iceberg", "sales", "secret")
    out = sync.execute(_catalog_wide())
    discovery = world.discoveries.get(CatalogDiscoveryId("iceberg"))
    assert out.dropped == 0
    assert discovery.current_failure is None
    assert discovery.last_discovered_at == now


def test_any_other_catalog_error_still_fails_the_scan(sync, world, monkeypatch):
    """An error that is neither a refusal nor a missing catalog fails the run, to be retried, and records nothing."""

    def broken(_input):
        raise RuntimeError("polaris unavailable")

    monkeypatch.setattr(world.catalog, "list_tables", broken)
    with pytest.raises(RuntimeError):
        sync.execute(_catalog_wide())
    assert world.discoveries.get(CatalogDiscoveryId("iceberg")) is None


# --- sync: unknown tables ---


def test_sync_registers_a_managed_table_and_sends_managed(sync, tables_repo, world, catalog, signals):
    """Sync registers a table its policy manages as managed and starts its workflow, sending ``managed``."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.renamed, out.dropped, out.skipped) == (1, 0, 0, 0)
    table = tables_repo.get(TableId("u-1"))
    assert table.status == TableStatus.MANAGED
    assert _position(table) == MANAGE_RULE
    assert _calls(signals) == [("u-1", "managed", True)]
    assert [c.table_name for c in signals.calls] == ["iceberg.sales.orders"]


def test_sync_registers_an_excluded_table_and_one_no_rule_matches_as_unmanaged(
    sync, tables_repo, world, catalog, signals
):
    """Sync records the tables an exclude rule decides, or that no rule matches, as unmanaged, and starts nothing."""
    world.attach_to_catalog(_policy("tmp-out", ("exclude", "tmp_*")))
    catalog.add_table("iceberg", "sales", "tmp_x", "u-1")
    catalog.add_table("iceberg", "sales", "orders", "u-2")
    out = sync.execute(_catalog_wide())
    assert out.registered == 2
    assert tables_repo.get(TableId("u-1")).status == TableStatus.UNMANAGED
    assert _position(tables_repo.get(TableId("u-1"))) == 1
    assert tables_repo.get(TableId("u-2")).status == TableStatus.UNMANAGED
    assert _position(tables_repo.get(TableId("u-2"))) is None
    assert signals.calls == []


def test_sync_leaves_a_registered_unmanaged_table_alone(sync, tables_repo, catalog, signals):
    """A second sync of a table nothing attached decides neither stores it again nor signals it."""
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.unmanaged, out.ensured) == (0, 0, 0)
    assert tables_repo.get(TableId("u-1")).status == TableStatus.UNMANAGED
    assert signals.calls == []


def test_sync_manages_a_registered_unmanaged_table_once_a_policy_manages_it(sync, tables_repo, world, catalog, signals):
    """A table first recorded as unmanaged is managed, and its workflow started, once a policy manages it."""
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    world.attach_to_catalog(MANAGE_ALL)
    out = sync.execute(_catalog_wide())
    assert out.managed == 1
    assert tables_repo.get(TableId("u-1")).status == TableStatus.MANAGED
    assert _calls(signals)[0] == ("u-1", "managed", True)


def test_namespace_sync_of_a_managed_table_does_not_reensure(sync, tables_repo, world, catalog, signals, now):
    """A namespace pass over a managed table it already knows does not signal the workflow."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_namespace())
    assert out.ensured == 0
    assert signals.calls == []


def test_sync_one_bad_table_is_skipped_not_fatal(sync, tables_repo, world, catalog, monkeypatch):
    """A table that fails to register is skipped and does not stop the sync."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "a_bad", "u-bad")
    catalog.add_table("iceberg", "sales", "b_ok", "u-ok")
    original = tables_repo.create

    def create(table):
        if table.id.value == "u-bad":
            raise ConflictError("boom")
        return original(table)

    monkeypatch.setattr(tables_repo, "create", create)
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.skipped) == (1, 1)
    assert tables_repo.get(TableId("u-ok")) is not None


def _race_updates_of(tables_repo, monkeypatch, uuid):
    """Make every save of the table ``uuid`` find that another writer saved it first."""
    original = tables_repo.update

    def update(table):
        if table.id.value == uuid:
            raise ConcurrentUpdateError(f"table {uuid} was changed by someone else")
        return original(table)

    monkeypatch.setattr(tables_repo, "update", update)


def test_a_table_changed_during_the_scan_is_skipped(
    sync, tables_repo, world, catalog, signals, monkeypatch, caplog, now
):
    """A table another writer saved while the scan decided it is skipped and logged; the others are still synced."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-raced", _name("old_raced"))
    _row(tables_repo, now, "u-ok", _name("old_ok"))
    catalog.add_table("iceberg", "sales", "raced", "u-raced")
    catalog.add_table("iceberg", "sales", "ok", "u-ok")
    _race_updates_of(tables_repo, monkeypatch, "u-raced")

    out = sync.execute(_catalog_wide())

    assert (out.registered, out.renamed, out.skipped, out.dropped, out.ensured) == (0, 1, 1, 0, 1)
    assert tables_repo.get(TableId("u-ok")).name.table == "ok"
    assert _calls(signals) == [("u-ok", "seen", True)]
    assert "table u-raced was changed by someone else" in caplog.text
    assert world.discoveries.get(CatalogDiscoveryId("iceberg")) is not None


def test_a_table_changed_while_the_scan_drops_it_is_skipped(sync, tables_repo, monkeypatch, signals, now):
    """A missing table another writer saved meanwhile is skipped, not dropped; the other missing table is dropped."""
    _row(tables_repo, now, "u-raced", _name("raced"))
    _row(tables_repo, now, "u-gone", _name("gone"))
    _race_updates_of(tables_repo, monkeypatch, "u-raced")

    out = sync.execute(_catalog_wide())

    assert (out.dropped, out.skipped) == (1, 1)
    assert _calls(signals) == [("u-gone", "stopped", False)]


def test_a_table_changed_while_an_unread_catalog_unmanages_it_is_skipped(
    sync, tables_repo, world, monkeypatch, signals, now
):
    """A catalog nothing can manage, which cannot be read, skips a managed table another writer saved meanwhile."""
    world.catalog.deny("iceberg")
    _row(tables_repo, now, "u-raced", _name("raced"))
    _row(tables_repo, now, "u-ok", _name("ok"))
    _race_updates_of(tables_repo, monkeypatch, "u-raced")

    out = sync.execute(_catalog_wide())

    assert (out.unmanaged, out.skipped) == (1, 1)
    assert _calls(signals) == [("u-ok", "stopped", False)]


# --- sync: known tables are decided again ---


def test_known_managed_table_becomes_unmanaged_when_its_policy_unmanages_it(
    sync, tables_repo, world, catalog, signals, log, now
):
    """A managed table its policy now unmanages is unmanaged, persisted once and told to stop."""
    world.attach_to_catalog(UNMANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    out = sync.execute(_catalog_wide())
    table = tables_repo.get(TableId("u-1"))
    assert table.status == TableStatus.UNMANAGED
    assert table.decided_by == DecidedBy(policy_id=UNMANAGE_ALL.id, policy_version=1, rule_position=1)
    assert (out.unmanaged, out.managed, out.ensured) == (1, 0, 0)
    assert _calls(signals) == [("u-1", "stopped", False)]
    assert log == [("tables.update", "u-1")]


def test_known_managed_table_with_nothing_attached_becomes_unmanaged(sync, tables_repo, catalog, signals, now):
    """A managed table with no attachment on its walk any more is unmanaged, decided by nothing."""
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    assert tables_repo.get(TableId("u-1")).status == TableStatus.UNMANAGED
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_unmanaged_table_is_managed_again_when_a_policy_manages_it(sync, tables_repo, world, catalog, signals, now):
    """An unmanaged table a policy now manages is managed again under its rule and its workflow started."""
    world.attach_to_catalog(ALL_BUT_TMP)
    _row(tables_repo, now, "u-1", _name("orders"), by=None)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_catalog_wide())
    table = tables_repo.get(TableId("u-1"))
    assert table.status == TableStatus.MANAGED
    assert _position(table) == REST_RULE
    assert (out.managed, out.unmanaged, out.ensured) == (1, 0, 0)
    assert _calls(signals) == [("u-1", "managed", True)]


def test_unmanaged_table_still_unmanaged_by_the_same_rule_is_left_alone(
    sync, tables_repo, world, catalog, signals, log, now
):
    """An unmanaged table the same policy, version and rule still unmanage is neither updated nor notified."""
    world.attach_to_catalog(UNMANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"), by=UNMANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    out = sync.execute(_catalog_wide())
    assert (out.managed, out.unmanaged, out.ensured) == (0, 0, 0)
    assert log == []
    assert signals.calls == []


def test_managed_table_now_decided_by_another_managing_policy_records_it(
    sync, tables_repo, world, catalog, signals, log, now
):
    """A managed table another managing policy now decides stores what decided it and stays managed."""
    world.attach_to_catalog(ALL_BUT_TMP)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    out = sync.execute(_catalog_wide())
    table = tables_repo.get(TableId("u-1"))
    assert (table.status, _position(table)) == (TableStatus.MANAGED, REST_RULE)
    assert (out.managed, out.unmanaged, out.ensured) == (0, 0, 1)
    assert log == [("tables.update", "u-1")]
    assert _calls(signals) == [("u-1", "seen", True)]


def test_namespace_pass_stores_a_decision_change_without_signalling(
    sync, tables_repo, world, catalog, signals, log, now
):
    """A change of only what decided the table is stored; a namespace pass does not signal the still-managed table."""
    world.attach_to_catalog(ALL_BUT_TMP)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    sync.execute(_namespace())
    assert _position(tables_repo.get(TableId("u-1"))) == REST_RULE
    assert log == [("tables.update", "u-1")]
    assert signals.calls == []


def test_unchanged_managed_table_is_not_stored_again(sync, tables_repo, world, catalog, log, now):
    """A managed table the same policy, version and rule still manage is not written."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    sync.execute(_catalog_wide())
    assert log == []


def test_sync_persists_rename(sync, tables_repo, world, catalog, log, now):
    """A rename found by sync is persisted with one update."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("old"))
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    catalog.add_table("iceberg", "sales", "new", "u-1")
    sync.execute(_catalog_wide())
    assert log == [("tables.update", "u-1")]


def test_sync_renames_and_unmanages_in_one_update(sync, tables_repo, catalog, signals, log, now):
    """A renamed table no policy manages any more is renamed and unmanaged in one update."""
    _row(tables_repo, now, "u-1", _name("old"))
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    catalog.add_table("iceberg", "sales", "new", "u-1")
    out = sync.execute(_catalog_wide())
    stored = tables_repo.get(TableId("u-1"))
    assert (stored.name.table, stored.status) == ("new", TableStatus.UNMANAGED)
    assert (out.renamed, out.unmanaged) == (1, 1)
    assert log == [("tables.update", "u-1")]
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_sync_dropped_row_whose_uuid_reappears_is_not_renamed_or_revived(
    sync, tables_repo, world, catalog, signals, now
):
    """A dropped row whose uuid reappears in the catalog is neither renamed nor revived."""
    world.attach_to_catalog(MANAGE_ALL)
    row = _row(tables_repo, now, "u-1", _name("old"))
    row.mark_dropped(now)
    catalog.add_table("iceberg", "sales", "new", "u-1")
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.renamed, out.dropped, out.skipped) == (0, 0, 0, 0)
    stored = tables_repo.get(TableId("u-1"))
    assert stored.status == TableStatus.DROPPED
    assert stored.name.table == "old"
    assert signals.calls == []


# --- sync: scope and drops ---


def test_sync_namespace_scope_never_drops(sync, tables_repo, signals, now):
    """A sync scoped to a namespace never drops tables."""
    _row(tables_repo, now, "u-in", _name("gone"))
    _row(tables_repo, now, "u-other-ns", _name("gone", namespace="hr"))
    out = sync.execute(_namespace())
    assert out.dropped == 0
    assert tables_repo.get(TableId("u-in")).status == TableStatus.MANAGED
    assert tables_repo.get(TableId("u-other-ns")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_namespace_pass_never_unmanages_missing_tables(sync, tables_repo, world, catalog, signals, now):
    """A namespace pass decides only the tables it lists; a known table it does not see keeps its status."""
    world.attach_to_catalog(UNMANAGE_ALL)
    _row(tables_repo, now, "u-missing", _name("gone"))
    _row(tables_repo, now, "u-other-ns", _name("elsewhere", namespace="hr"))
    catalog.add_table("iceberg", "hr", "elsewhere", "u-other-ns")
    out = sync.execute(_namespace())
    assert (out.unmanaged, out.dropped) == (0, 0)
    assert tables_repo.get(TableId("u-missing")).status == TableStatus.MANAGED
    assert tables_repo.get(TableId("u-other-ns")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_sync_namespace_scope_still_registers_renames_and_decides(sync, tables_repo, world, catalog, now):
    """A sync scoped to a namespace still registers, renames and decides the tables it lists."""
    world.attach_to_catalog(ALL_BUT_TMP)
    _row(tables_repo, now, "u-1", _name("old"), by=ALL_BUT_TMP)
    _row(tables_repo, now, "u-3", _name("tmp_x"))
    catalog.add_table("iceberg", "sales", "new", "u-1")
    catalog.add_table("iceberg", "sales", "fresh", "u-2")
    catalog.add_table("iceberg", "sales", "tmp_x", "u-3")
    out = sync.execute(_namespace())
    assert (out.registered, out.renamed, out.unmanaged, out.dropped) == (1, 1, 1, 0)


def test_sync_namespace_scope_signals_management_changes(sync, tables_repo, world, catalog, signals, now):
    """A namespace pass starts the workflow of a table managed again and stops one unmanaged."""
    world.attach_to_catalog(ONLY_BACK)
    _row(tables_repo, now, "u-back", _name("back"), by=None)
    _row(tables_repo, now, "u-out", _name("out"))
    catalog.add_table("iceberg", "sales", "back", "u-back")
    catalog.add_table("iceberg", "sales", "out", "u-out")
    sync.execute(_namespace())
    assert sorted(_calls(signals)) == [("u-back", "managed", True), ("u-out", "stopped", False)]


def test_sync_catalog_wide_drops_only_rows_of_that_catalog(sync, tables_repo, signals, now):
    """A catalog-wide sync drops only the rows of that catalog that are gone."""
    _row(tables_repo, now, "u-1", _name("gone"))
    _row(tables_repo, now, "u-2", _name("gone", namespace="hr"))
    _row(tables_repo, now, "u-other-cat", TableName(catalog="other", namespace="sales", table="gone"))
    out = sync.execute(_catalog_wide())
    assert out.dropped == 2
    assert tables_repo.get(TableId("u-1")).status == TableStatus.DROPPED
    assert tables_repo.get(TableId("u-2")).status == TableStatus.DROPPED
    assert tables_repo.get(TableId("u-other-cat")).status == TableStatus.MANAGED
    assert sorted(_calls(signals)) == [
        ("u-1", "stopped", False),
        ("u-2", "stopped", False),
    ]


def test_sync_drops_unmanaged_without_stop_signal_and_ignores_dropped(sync, tables_repo, signals, now):
    """Sync drops an unmanaged table without a stop signal and ignores tables already dropped."""
    _row(tables_repo, now, "u-1", _name("x"), by=None)
    already = _row(tables_repo, now, "u-2", _name("y"))
    already.mark_dropped(now)
    out = sync.execute(_catalog_wide())
    assert out.dropped == 1
    assert tables_repo.get(TableId("u-1")).status == TableStatus.DROPPED
    assert signals.calls == []


# --- sync: reconciliation workflow is (re-)ensured ---


def _fail_first_send(signals, monkeypatch):
    original = signals.send
    failed: list[bool] = []

    def send(input):  # noqa: A002
        if not failed:
            failed.append(True)
            raise RuntimeError("temporal unavailable")
        original(input)

    monkeypatch.setattr(signals, "send", send)


def test_sync_retry_after_failed_start_still_starts_workflow(sync, tables_repo, world, catalog, signals, monkeypatch):
    """A sync retried after a failed workflow start still starts the workflow."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    _fail_first_send(signals, monkeypatch)
    with pytest.raises(RuntimeError):
        sync.execute(_catalog_wide())
    assert tables_repo.get(TableId("u-1")) is not None
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.ensured) == (0, 1)
    assert _calls(signals) == [("u-1", "seen", True)]


def test_sync_reensures_workflow_of_every_managed_table(sync, tables_repo, world, catalog, signals, now):
    """Sync makes sure every managed table has its workflow, and only those."""
    world.attach_to_catalog(ALL_BUT_TMP)
    _row(tables_repo, now, "u-managed", _name("a"), by=ALL_BUT_TMP)
    _row(tables_repo, now, "u-other", _name("b"), by=ALL_BUT_TMP)
    _row(tables_repo, now, "u-unmanaged", _name("tmp_x"), by=ALL_BUT_TMP)
    _row(tables_repo, now, "u-dropped", _name("d")).mark_dropped(now)
    for uuid, name in (("u-managed", "a"), ("u-other", "b"), ("u-unmanaged", "tmp_x"), ("u-dropped", "d")):
        catalog.add_table("iceberg", "sales", name, uuid)
    out = sync.execute(_catalog_wide())
    assert out.ensured == 2
    assert sorted(_calls(signals)) == [("u-managed", "seen", True), ("u-other", "seen", True)]


def test_sync_reensures_renamed_table(sync, tables_repo, world, catalog, signals, now):
    """Sync re-ensures the workflow of a renamed table."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("old"))
    catalog.add_table("iceberg", "sales", "new", "u-1")
    out = sync.execute(_catalog_wide())
    assert (out.renamed, out.ensured) == (1, 1)
    assert _calls(signals) == [("u-1", "seen", True)]


def test_sync_does_not_reensure_freshly_registered_table_twice(sync, world, catalog, signals):
    """A table registered by sync is not ensured a second time."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.ensured) == (1, 0)
    assert _calls(signals) == [("u-1", "managed", True)]


def test_sync_namespace_scope_does_not_reensure(sync, tables_repo, world, catalog, signals, now):
    """A sync scoped to a namespace does not re-ensure workflows of tables whose management is unchanged."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_namespace())
    assert out.ensured == 0
    assert signals.calls == []


# --- table hint ---


@pytest.fixture
def hint(tables_repo, discovery_policies, discovery_attachments, catalog, signals, discovery_requests, clock):
    """Provide the process table hint service on the fakes."""
    return ProcessTableHintService(
        tables_repo,
        discovery_policies,
        discovery_attachments,
        catalog,
        signals,
        discovery_requests,
        clock=clock,
    )


def _hint(table="orders", namespace="sales", event_type="updateTable"):
    return ProcessTableHintUseCaseInput(catalog="iceberg", namespace=namespace, table=table, event_type=event_type)


def test_a_hint_in_an_unscanned_catalog_registers_unmanaged(hint, world, signals):
    """A catalog event in a catalog with no policy registers the table, decided by nothing, and sends nothing."""
    world.attach(catalog_target("other"), MANAGE_ALL)
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "registered"
    table = world.tables.get(TableId("u-1"))
    assert (table.status, table.decided_by) == (TableStatus.UNMANAGED, None)
    assert signals.calls == []


def test_a_hint_decides_a_table_moved_out_of_a_managing_namespace_by_its_new_name(
    hint, world, tables_repo, signals, now
):
    """A catalog event decides a known table by the name the catalog gives it now, not the name stored for it."""
    world.attach(namespace_target("iceberg", "sales"), MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    world.catalog.add_table("iceberg", "other", "orders", "u-1")
    assert hint.execute(_hint(namespace="other")).action == "unmanaged"
    table = world.tables.get(TableId("u-1"))
    assert (table.name.namespace, table.status) == ("other", TableStatus.UNMANAGED)
    assert table.decided_by is None
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_a_hint_reads_the_walk_of_a_table_moved_into_a_managing_namespace(hint, world, tables_repo, signals, now):
    """A catalog event reads the attachments on the walk of the new name: a move into a managed namespace manages it."""
    world.attach(namespace_target("iceberg", "other"), MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"), by=None)
    world.catalog.add_table("iceberg", "other", "orders", "u-1")
    assert hint.execute(_hint(namespace="other")).action == "managed"
    expected = MANAGE_ALL.should_manage(_name("orders", namespace="other")).decided_by
    assert world.tables.get(TableId("u-1")).decided_by == expected
    assert _calls(signals) == [("u-1", "managed", True)]


def test_a_hint_decides_a_new_table_by_its_uuid(hint, world, signals):
    """A catalog event finds the table's own attachment by its uuid: an exclude on it opts it out of its namespace."""
    world.attach(namespace_target("iceberg", "sales"), MANAGE_ALL)
    world.attach(table_target(_name("orders"), "u-1"), UNMANAGE_ALL)
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "registered"
    table = world.tables.get(TableId("u-1"))
    assert (table.status, table.decided_by) == (
        TableStatus.UNMANAGED,
        DecidedBy(policy_id=UNMANAGE_ALL.id, policy_version=1, rule_position=1),
    )
    assert signals.calls == []


def test_a_hint_reads_only_the_attachments_on_the_tables_walk(hint, world, log):
    """A hint decides its one table from the attachments on its walk, read in one call, and their policies in one."""
    world.attach(namespace_target("iceberg", "sales"), MANAGE_ALL)
    world.catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(world.attachments, "list_in_catalog", "attachments.list_in_catalog", log, str)
    track_calls(world.attachments, "get_many_by_targets", "attachments.get_many_by_targets", log, lambda t: str(len(t)))
    track_calls(world.policies, "get_many", "policies.get_many", log, lambda ids: str(len(ids)))
    hint.execute(_hint())
    assert log == [("attachments.get_many_by_targets", "3"), ("policies.get_many", "1")]
    assert world.tables.get(TableId("u-1")).is_managed


def test_table_hint_without_name_requests_namespace_discovery(hint, discovery_requests, signals):
    """A hint without a table name requests discovery of the namespace."""
    out = hint.execute(_hint(table=None, event_type="createNamespace"))
    assert out.action == "discovery_requested"
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [("iceberg", "sales")]
    assert signals.calls == []


def test_table_hint_for_managed_table_signals_table_updated(hint, tables_repo, world, catalog, signals, now):
    """A hint for a managed table signals that the table was updated."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = hint.execute(_hint())
    assert out.action == "notified"
    assert _calls(signals) == [("u-1", "updated", True)]
    assert [c.table_name for c in signals.calls] == ["iceberg.sales.orders"]


def test_table_hint_for_unmanaged_table_still_unmanaged_is_ignored(hint, tables_repo, world, catalog, signals, now):
    """A hint for an unmanaged table the same policy and rule still leave unmanaged is ignored."""
    world.attach_to_catalog(UNMANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"), by=UNMANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "ignored"
    assert signals.calls == []


def test_table_hint_saves_a_decision_change_of_an_unmanaged_table_and_sends_nothing(
    hint, tables_repo, world, catalog, signals, log, now
):
    """A hint for an unmanaged table another policy now leaves unmanaged saves what decides it, and sends nothing."""
    world.attach_to_catalog(ONLY_BACK)
    _row(tables_repo, now, "u-1", _name("orders"), by=UNMANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    assert hint.execute(_hint()).action == "ignored"
    stored = tables_repo.get(TableId("u-1"))
    assert (stored.status, stored.decided_by) == (
        TableStatus.UNMANAGED,
        DecidedBy(policy_id=ONLY_BACK.id, policy_version=1, rule_position=None),
    )
    assert log == [("tables.update", "u-1")]
    assert signals.calls == []


def test_table_hint_unmanages_a_managed_table_its_policy_unmanages(hint, tables_repo, world, catalog, signals, now):
    """A hint decides the table it names: an unmanaging decision unmanages it and stops its workflow."""
    world.attach_to_catalog(UNMANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "unmanaged"
    assert tables_repo.get(TableId("u-1")).status == TableStatus.UNMANAGED
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_table_hint_manages_an_unmanaged_table_its_policy_manages(hint, tables_repo, world, catalog, signals, now):
    """A hint for an unmanaged table a policy now manages manages it again and starts its workflow."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"), by=None)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "managed"
    assert tables_repo.get(TableId("u-1")).status == TableStatus.MANAGED
    assert _calls(signals) == [("u-1", "managed", True)]


def test_table_hint_registers_a_new_table_no_policy_manages_as_unmanaged(hint, tables_repo, catalog, signals):
    """A hint for a new table no policy manages records it as unmanaged and starts no workflow."""
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "registered"
    assert tables_repo.get(TableId("u-1")).status == TableStatus.UNMANAGED
    assert signals.calls == []


def _busy_observation(uuid):
    return TableMetadataObservation(
        table_uuid=uuid,
        specs=[{"spec_id": 0, "fields": []}],
        partitions=[
            {
                "spec_id": 0,
                "values": [],
                "data_file_count": 50,
                "position_delete_file_count": 0,
                "equality_delete_file_count": 0,
                "total_data_file_size_bytes": 50 * 1024,
            }
        ],
    )


def test_table_hint_for_managed_table_signals_but_cooldown_blocks_replan(
    hint, tables_repo, world, catalog, signals, resolve_applicable_policy, now
):
    """A hint signals the workflow, while a cooldown still blocks a new plan."""
    world.attach_to_catalog(MANAGE_ALL)
    cooling = _row(tables_repo, now, "u-1", _name("orders"))
    for op in MaintenanceOperation.ordered():
        cooling.record_operation_result(op, True, now - timedelta(minutes=1), size=ComputeSize.S)
    _row(tables_repo, now, "u-2", _name("fresh"))
    for uuid, name in (("u-1", "orders"), ("u-2", "fresh")):
        catalog.add_table("iceberg", "sales", name, uuid)
        catalog.observations[("iceberg", "sales", name)] = _busy_observation(uuid)
    assert hint.execute(_hint()).action == "notified"
    assert _calls(signals) == [("u-1", "updated", True)]
    planner = plan_service_on_fakes(tables_repo, catalog, resolve_applicable_policy)
    blocked = planner.execute(PlanTableMaintenanceUseCaseInput(table_uuid="u-1", now=now))
    assert (blocked.status, blocked.operations) == ("planned", ())
    control = planner.execute(PlanTableMaintenanceUseCaseInput(table_uuid="u-2", now=now))
    assert "rewrite_data_files" in [o.operation for o in control.operations]


def test_table_hint_with_new_name_renames_then_signals(hint, tables_repo, world, catalog, signals, now):
    """A hint with a new table name renames the row and then signals."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("old"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = hint.execute(_hint())
    assert out.action == "renamed"
    assert tables_repo.get(TableId("u-1")).name.table == "orders"
    assert _calls(signals) == [("u-1", "updated", True)]


def test_table_hint_registers_unregistered_table_by_its_policy(hint, tables_repo, world, catalog, signals):
    """A hint for an unregistered table registers it as managed by its policy and sends ``managed``."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "registered"
    assert tables_repo.get(TableId("u-1")).status == TableStatus.MANAGED
    assert _calls(signals) == [("u-1", "managed", True)]


def test_table_hint_for_missing_table_with_row_requests_discovery(hint, tables_repo, discovery_requests, now):
    """A hint for a table gone from the catalog but still stored requests discovery."""
    _row(tables_repo, now, "u-1", _name("orders"))
    out = hint.execute(_hint())
    assert out.action == "discovery_requested"
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [("iceberg", None)]


def test_table_hint_for_missing_unknown_table_is_ignored(hint, discovery_requests):
    """A hint for a table that is neither in the catalog nor stored is ignored."""
    assert hint.execute(_hint()).action == "ignored"
    assert discovery_requests.calls == []


def test_table_hint_for_dropped_registered_row_is_ignored(hint, tables_repo, catalog, signals, now):
    """A hint for a dropped row is ignored."""
    _row(tables_repo, now, "u-1", _name("orders")).mark_dropped(now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "ignored"
    assert signals.calls == []


def test_table_hint_new_uuid_over_live_same_name_row_requests_catalog_discovery(
    hint, tables_repo, world, catalog, discovery_requests, now
):
    """A new uuid under the name of a live row registers it and requests a catalog discovery."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-old", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-new")
    assert hint.execute(_hint()).action == "registered"
    assert tables_repo.get(TableId("u-new")) is not None
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [("iceberg", None)]


def test_table_hint_fresh_registration_requests_no_discovery(hint, world, catalog, discovery_requests):
    """A fresh registration requests no discovery."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    hint.execute(_hint())
    assert discovery_requests.calls == []


def test_table_hint_persists_rename(hint, tables_repo, world, catalog, log, now):
    """A rename found through a hint is persisted with one update."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("old"))
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    hint.execute(_hint())
    assert log == [("tables.update", "u-1")]


def test_table_hint_retry_after_failed_start_still_starts_workflow(
    hint, tables_repo, world, catalog, signals, monkeypatch
):
    """A hint retried after a failed workflow start still signals the workflow."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    _fail_first_send(signals, monkeypatch)
    with pytest.raises(RuntimeError):
        hint.execute(_hint())
    assert tables_repo.get(TableId("u-1")) is not None
    assert hint.execute(_hint()).action == "notified"
    assert _calls(signals) == [("u-1", "updated", True)]


# --- what discovery tells the reconciliation ---


def test_a_scan_that_registers_a_managed_table_sends_managed(sync, world, catalog, signals):
    """A scan that registers a table as managed sends ``managed``, so the table is checked at once."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_namespace())
    assert _calls(signals) == [("u-1", "managed", True)]


def test_a_hint_that_registers_a_managed_table_sends_managed(hint, world, catalog, signals):
    """A catalog event that registers a table as managed sends ``managed``, not ``updated``."""
    world.attach_to_catalog(MANAGE_ALL)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    hint.execute(_hint())
    assert _calls(signals) == [("u-1", "managed", True)]


def test_a_table_managed_again_sends_managed(sync, tables_repo, world, catalog, signals, now):
    """An unmanaged table a policy now manages is sent ``managed``."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"), by=None)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    assert _calls(signals) == [("u-1", "managed", True)]


def test_a_scan_of_a_managed_table_sends_seen(sync, tables_repo, world, catalog, signals, now):
    """A catalog-wide scan of an unchanged managed table sends ``seen``, which only keeps its workflow."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    assert _calls(signals) == [("u-1", "seen", True)]


def test_a_commit_hint_for_a_managed_table_sends_updated(hint, tables_repo, world, catalog, signals, now):
    """A catalog event for a table already managed sends ``updated``."""
    world.attach_to_catalog(MANAGE_ALL)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    hint.execute(_hint())
    assert _calls(signals) == [("u-1", "updated", True)]
