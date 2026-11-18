"""Test the discovery sync and table hint services: the discovery rules alone decide managed tables."""

from __future__ import annotations

from datetime import timedelta

import pytest

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rules import (
    GlobList,
    RuleAction,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.exceptions import ConflictError
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCaseInput,
    ProcessTableHintUseCaseInput,
    SyncDiscoveredTablesUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table import (
    CatalogNotFoundError,
    TableMetadataObservation,
)
from context.table_maintenance.application.service.table import (
    ProcessTableHintService,
    SyncDiscoveredTablesService,
)
from tests.context.table_maintenance.fakes.plan_service_on_fakes import plan_service_on_fakes
from tests.context.table_maintenance.fakes.track_calls import track_calls


def _rule(rules_repo, now, action, tables=("*",), rid="r-1", priority=10):  # noqa: PLR0913
    """Add one enabled rule to the saved discovery rules."""
    every = GlobList(globs=("*",))
    rule = TableDiscoveryRule.create(
        id=TableDiscoveryRuleId(rid),
        priority=priority,
        action=action,
        enabled=True,
        catalogs=every,
        namespaces=every,
        tables=GlobList(globs=tables),
        now=now,
    )
    rules = rules_repo.get_rules()
    rules.replace((*rules.rules, rule), rules.version, now, new_ids={rule.id})
    rules_repo.save(rules)


def _include_all(rules_repo, now):
    _rule(rules_repo, now, RuleAction.INCLUDE)


def _exclude_all(rules_repo, now, rid="r-ex"):
    _rule(rules_repo, now, RuleAction.EXCLUDE, rid=rid, priority=1)


def _row(repo, now, uuid, name, *, unmanaged=False):
    table = Table.register(TableId(uuid), name, TableDiscoveryRuleId("r-1"), now)
    if unmanaged:
        table.unmanage(now)
    repo.create(table)
    return table


def _name(table, namespace="sales"):
    return TableName(catalog="iceberg", namespace=namespace, table=table)


@pytest.fixture
def sync(tables_repo, rules_repo, discoveries_repo, catalog, signals, clock):
    """Provide the sync discovered tables service on the fakes."""
    return SyncDiscoveredTablesService(
        tables_repo,
        rules_repo,
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


# --- sync: unknown tables ---


def test_sync_of_unknown_catalog_fails_and_drops_nothing(sync, tables_repo, catalog, signals, now, monkeypatch):
    """A catalog the gateway cannot open fails the run; it does not read as every table vanishing."""
    _row(tables_repo, now, "u-1", _name("kept"))

    def unknown(_input):
        raise CatalogNotFoundError("iceberg")

    monkeypatch.setattr(catalog, "list_tables", unknown)
    with pytest.raises(CatalogNotFoundError):
        sync.execute(_catalog_wide())
    assert tables_repo.get(TableId("u-1")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_sync_registers_include_match_as_managed(sync, tables_repo, rules_repo, catalog, signals, now):
    """Sync registers a table an include rule matches as managed and starts its workflow."""
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.renamed, out.dropped, out.skipped) == (1, 0, 0, 0)
    table = tables_repo.get(TableId("u-1"))
    assert table.status == TableStatus.MANAGED
    assert table.matched_rule_id == TableDiscoveryRuleId("r-1")
    assert _calls(signals) == [("u-1", "seen", True)]
    assert [c.table_name for c in signals.calls] == ["iceberg.sales.orders"]


def test_sync_registers_exclude_match_and_no_match_as_unmanaged(sync, tables_repo, rules_repo, catalog, signals, now):
    """Sync records tables an exclude rule or no rule decides as unmanaged, and starts no workflow."""
    _rule(rules_repo, now, RuleAction.EXCLUDE, ("tmp_*",))
    catalog.add_table("iceberg", "sales", "tmp_x", "u-1")
    catalog.add_table("iceberg", "sales", "orders", "u-2")
    out = sync.execute(_catalog_wide())
    assert out.registered == 2
    for uuid in ("u-1", "u-2"):
        table = tables_repo.get(TableId(uuid))
        assert table.status == TableStatus.UNMANAGED
        assert table.matched_rule_id is None
    assert signals.calls == []


def test_sync_leaves_a_registered_unmanaged_table_alone(sync, tables_repo, catalog, signals, log, now):
    """A second sync of a table no rule decides neither stores it again nor signals it."""
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.unmanaged, out.ensured) == (0, 0, 0)
    assert tables_repo.get(TableId("u-1")).status == TableStatus.UNMANAGED
    assert signals.calls == []


def test_sync_manages_a_registered_unmanaged_table_once_a_rule_includes_it(
    sync, tables_repo, rules_repo, catalog, signals, now
):
    """A table first recorded as unmanaged is managed, and its workflow started, when a rule includes it."""
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    _include_all(rules_repo, now)
    out = sync.execute(_catalog_wide())
    assert out.managed == 1
    assert tables_repo.get(TableId("u-1")).status == TableStatus.MANAGED
    assert _calls(signals)[0] == ("u-1", "seen", True)


def test_namespace_sync_of_a_managed_table_does_not_reensure(sync, tables_repo, rules_repo, catalog, signals, now):
    """A namespace pass over a managed table it already knows does not signal the workflow."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_namespace())
    assert out.ensured == 0
    assert signals.calls == []


def test_sync_one_bad_table_is_skipped_not_fatal(sync, tables_repo, rules_repo, catalog, now, monkeypatch):
    """A table that fails to register is skipped and does not stop the sync."""
    _include_all(rules_repo, now)
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


# --- sync: known tables are decided again ---


def test_known_managed_table_becomes_unmanaged_when_rule_excludes_it(
    sync, tables_repo, rules_repo, catalog, signals, log, now
):
    """A managed table an exclude rule now decides is unmanaged, persisted once and told to stop."""
    _include_all(rules_repo, now)
    _exclude_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    out = sync.execute(_catalog_wide())
    table = tables_repo.get(TableId("u-1"))
    assert table.status == TableStatus.UNMANAGED
    assert table.matched_rule_id is None
    assert (out.unmanaged, out.managed, out.ensured) == (1, 0, 0)
    assert _calls(signals) == [("u-1", "stopped", False)]
    assert log == [("tables.update", "u-1")]


def test_known_managed_table_without_any_matching_rule_becomes_unmanaged(sync, tables_repo, catalog, signals, now):
    """A managed table no rule matches any more is unmanaged."""
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    sync.execute(_catalog_wide())
    assert tables_repo.get(TableId("u-1")).status == TableStatus.UNMANAGED
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_unmanaged_table_is_managed_again_when_rule_includes_it(sync, tables_repo, rules_repo, catalog, signals, now):
    """An unmanaged table an include rule now decides is managed again and its workflow started."""
    _rule(rules_repo, now, RuleAction.INCLUDE, rid="r-2")
    _row(tables_repo, now, "u-1", _name("orders"), unmanaged=True)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_catalog_wide())
    table = tables_repo.get(TableId("u-1"))
    assert table.status == TableStatus.MANAGED
    assert table.matched_rule_id == TableDiscoveryRuleId("r-2")
    assert (out.managed, out.unmanaged, out.ensured) == (1, 0, 0)
    assert _calls(signals) == [("u-1", "seen", True)]


def test_unmanaged_table_still_excluded_is_left_alone(sync, tables_repo, rules_repo, catalog, signals, log, now):
    """An unmanaged table the rules still exclude is neither updated nor signalled."""
    _exclude_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"), unmanaged=True)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    out = sync.execute(_catalog_wide())
    assert (out.managed, out.unmanaged, out.ensured) == (0, 0, 0)
    assert log == []
    assert signals.calls == []


def test_managed_table_now_decided_by_another_include_rule_records_it(
    sync, tables_repo, rules_repo, catalog, signals, log, now
):
    """A managed table matched first by another include rule stores that rule and stays managed."""
    _rule(rules_repo, now, RuleAction.INCLUDE, rid="r-2", priority=1)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    out = sync.execute(_catalog_wide())
    table = tables_repo.get(TableId("u-1"))
    assert (table.status, table.matched_rule_id) == (TableStatus.MANAGED, TableDiscoveryRuleId("r-2"))
    assert (out.managed, out.unmanaged, out.ensured) == (0, 0, 1)
    assert log == [("tables.update", "u-1")]
    assert _calls(signals) == [("u-1", "seen", True)]


def test_namespace_pass_stores_a_rule_change_without_signalling(
    sync, tables_repo, rules_repo, catalog, signals, log, now
):
    """A rule-only change is stored; a namespace pass does not signal the still-managed table."""
    _rule(rules_repo, now, RuleAction.INCLUDE, rid="r-2", priority=1)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    sync.execute(_namespace())
    assert tables_repo.get(TableId("u-1")).matched_rule_id == TableDiscoveryRuleId("r-2")
    assert log == [("tables.update", "u-1")]
    assert signals.calls == []


def test_unchanged_managed_table_is_not_stored_again(sync, tables_repo, rules_repo, catalog, log, now):
    """A managed table the same include rule still decides is not written."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    sync.execute(_catalog_wide())
    assert log == []


def test_sync_persists_rename(sync, tables_repo, rules_repo, catalog, log, now):
    """A rename found by sync is persisted with one update."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("old"))
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    catalog.add_table("iceberg", "sales", "new", "u-1")
    sync.execute(_catalog_wide())
    assert log == [("tables.update", "u-1")]


def test_sync_renames_and_unmanages_in_one_update(sync, tables_repo, catalog, signals, log, now):
    """A renamed table the rules no longer include is renamed and unmanaged in one update."""
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
    sync, tables_repo, rules_repo, catalog, signals, now
):
    """A dropped row whose uuid reappears in the catalog is neither renamed nor revived."""
    _include_all(rules_repo, now)
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


def test_sync_namespace_scope_never_drops(sync, tables_repo, catalog, signals, now):
    """A sync scoped to a namespace never drops tables."""
    _row(tables_repo, now, "u-in", _name("gone"))
    _row(tables_repo, now, "u-other-ns", _name("gone", namespace="hr"))
    out = sync.execute(_namespace())
    assert out.dropped == 0
    assert tables_repo.get(TableId("u-in")).status == TableStatus.MANAGED
    assert tables_repo.get(TableId("u-other-ns")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_namespace_pass_never_unmanages_missing_tables(sync, tables_repo, rules_repo, catalog, signals, now):
    """A namespace pass decides only the tables it lists; a known table it does not see keeps its status."""
    _exclude_all(rules_repo, now)
    _row(tables_repo, now, "u-missing", _name("gone"))
    _row(tables_repo, now, "u-other-ns", _name("elsewhere", namespace="hr"))
    catalog.add_table("iceberg", "hr", "elsewhere", "u-other-ns")
    out = sync.execute(_namespace())
    assert (out.unmanaged, out.dropped) == (0, 0)
    assert tables_repo.get(TableId("u-missing")).status == TableStatus.MANAGED
    assert tables_repo.get(TableId("u-other-ns")).status == TableStatus.MANAGED
    assert signals.calls == []


def test_sync_namespace_scope_still_registers_renames_and_decides(sync, tables_repo, rules_repo, catalog, now):
    """A sync scoped to a namespace still registers, renames and decides the tables it lists."""
    _include_all(rules_repo, now)
    _rule(rules_repo, now, RuleAction.EXCLUDE, ("tmp_*",), rid="r-ex", priority=1)
    _row(tables_repo, now, "u-1", _name("old"))
    _row(tables_repo, now, "u-3", _name("tmp_x"))
    catalog.add_table("iceberg", "sales", "new", "u-1")
    catalog.add_table("iceberg", "sales", "fresh", "u-2")
    catalog.add_table("iceberg", "sales", "tmp_x", "u-3")
    out = sync.execute(_namespace())
    assert (out.registered, out.renamed, out.unmanaged, out.dropped) == (1, 1, 1, 0)


def test_sync_namespace_scope_signals_management_changes(sync, tables_repo, rules_repo, catalog, signals, now):
    """A namespace pass starts the workflow of a table managed again and stops one unmanaged."""
    _rule(rules_repo, now, RuleAction.INCLUDE, ("back",))
    _row(tables_repo, now, "u-back", _name("back"), unmanaged=True)
    _row(tables_repo, now, "u-out", _name("out"))
    catalog.add_table("iceberg", "sales", "back", "u-back")
    catalog.add_table("iceberg", "sales", "out", "u-out")
    sync.execute(_namespace())
    assert sorted(_calls(signals)) == [("u-back", "seen", True), ("u-out", "stopped", False)]


def test_sync_catalog_wide_drops_only_rows_of_that_catalog(sync, tables_repo, catalog, signals, now):
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


def test_sync_drops_unmanaged_without_stop_signal_and_ignores_dropped(sync, tables_repo, catalog, signals, now):
    """Sync drops an unmanaged table without a stop signal and ignores tables already dropped."""
    _row(tables_repo, now, "u-1", _name("x"), unmanaged=True)
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


def test_sync_retry_after_failed_start_still_starts_workflow(
    sync, tables_repo, rules_repo, catalog, signals, now, monkeypatch
):
    """A sync retried after a failed workflow start still starts the workflow."""
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    _fail_first_send(signals, monkeypatch)
    with pytest.raises(RuntimeError):
        sync.execute(_catalog_wide())
    assert tables_repo.get(TableId("u-1")) is not None
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.ensured) == (0, 1)
    assert _calls(signals) == [("u-1", "seen", True)]


def test_sync_reensures_workflow_of_every_managed_table(sync, tables_repo, rules_repo, catalog, signals, now):
    """Sync makes sure every managed table has its workflow, and only those."""
    _include_all(rules_repo, now)
    _rule(rules_repo, now, RuleAction.EXCLUDE, ("x",), rid="r-ex", priority=1)
    _row(tables_repo, now, "u-managed", _name("a"))
    _row(tables_repo, now, "u-other", _name("b"))
    _row(tables_repo, now, "u-unmanaged", _name("x"), unmanaged=True)
    _row(tables_repo, now, "u-dropped", _name("d")).mark_dropped(now)
    for uuid, name in (("u-managed", "a"), ("u-other", "b"), ("u-unmanaged", "x"), ("u-dropped", "d")):
        catalog.add_table("iceberg", "sales", name, uuid)
    out = sync.execute(_catalog_wide())
    assert out.ensured == 2
    assert sorted(_calls(signals)) == [("u-managed", "seen", True), ("u-other", "seen", True)]


def test_sync_reensures_renamed_table(sync, tables_repo, rules_repo, catalog, signals, now):
    """Sync re-ensures the workflow of a renamed table."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("old"))
    catalog.add_table("iceberg", "sales", "new", "u-1")
    out = sync.execute(_catalog_wide())
    assert (out.renamed, out.ensured) == (1, 1)
    assert _calls(signals) == [("u-1", "seen", True)]


def test_sync_does_not_reensure_freshly_registered_table_twice(sync, rules_repo, catalog, signals, now):
    """A table registered by sync is not ensured a second time."""
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_catalog_wide())
    assert (out.registered, out.ensured) == (1, 0)
    assert _calls(signals) == [("u-1", "seen", True)]


def test_sync_namespace_scope_does_not_reensure(sync, tables_repo, rules_repo, catalog, signals, now):
    """A sync scoped to a namespace does not re-ensure workflows of tables whose management is unchanged."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(_namespace())
    assert out.ensured == 0
    assert signals.calls == []


# --- table hint ---


@pytest.fixture
def hint(tables_repo, rules_repo, catalog, signals, discovery_requests, clock):
    """Provide the process table hint service on the fakes."""
    return ProcessTableHintService(
        tables_repo,
        rules_repo,
        catalog,
        signals,
        discovery_requests,
        clock=clock,
    )


def _hint(table="orders", namespace="sales", event_type="updateTable"):
    return ProcessTableHintUseCaseInput(catalog="iceberg", namespace=namespace, table=table, event_type=event_type)


def test_table_hint_without_name_requests_namespace_discovery(hint, discovery_requests, signals):
    """A hint without a table name requests discovery of the namespace."""
    out = hint.execute(_hint(table=None, event_type="createNamespace"))
    assert out.action == "discovery_requested"
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [("iceberg", "sales")]
    assert signals.calls == []


def test_table_hint_for_managed_table_signals_table_updated(hint, tables_repo, rules_repo, catalog, signals, now):
    """A hint for a managed table signals that the table was updated."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = hint.execute(_hint())
    assert out.action == "signalled"
    assert _calls(signals) == [("u-1", "updated", True)]
    assert [c.table_name for c in signals.calls] == ["iceberg.sales.orders"]


def test_table_hint_for_unmanaged_table_still_excluded_is_ignored(hint, tables_repo, rules_repo, catalog, signals, now):
    """A hint for an unmanaged table the rules still exclude is ignored."""
    _exclude_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"), unmanaged=True)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "ignored"
    assert signals.calls == []


def test_table_hint_unmanages_a_managed_table_the_rules_exclude(hint, tables_repo, rules_repo, catalog, signals, now):
    """A hint applies the rules to the table it names: an exclude match unmanages it and stops its workflow."""
    _exclude_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "unmanaged"
    assert tables_repo.get(TableId("u-1")).status == TableStatus.UNMANAGED
    assert _calls(signals) == [("u-1", "stopped", False)]


def test_table_hint_manages_an_unmanaged_table_the_rules_include(hint, tables_repo, rules_repo, catalog, signals, now):
    """A hint for an unmanaged table an include rule now decides manages it again and starts its workflow."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("orders"), unmanaged=True)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "managed"
    assert tables_repo.get(TableId("u-1")).status == TableStatus.MANAGED
    assert _calls(signals) == [("u-1", "updated", True)]


def test_table_hint_registers_a_new_table_no_rule_includes_as_unmanaged(hint, tables_repo, catalog, signals, now):
    """A hint for a new table no rule includes records it as unmanaged and starts no workflow."""
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
    hint, tables_repo, rules_repo, catalog, signals, resolve_applicable_policy, now
):
    """A hint signals the workflow, while a cooldown still blocks a new plan."""
    _include_all(rules_repo, now)
    cooling = _row(tables_repo, now, "u-1", _name("orders"))
    for op in MaintenanceOperation.ordered():
        cooling.record_operation_result(op, True, now - timedelta(minutes=1))
    _row(tables_repo, now, "u-2", _name("fresh"))
    for uuid, name in (("u-1", "orders"), ("u-2", "fresh")):
        catalog.add_table("iceberg", "sales", name, uuid)
        catalog.observations[("iceberg", "sales", name)] = _busy_observation(uuid)
    assert hint.execute(_hint()).action == "signalled"
    assert _calls(signals) == [("u-1", "updated", True)]
    planner = plan_service_on_fakes(tables_repo, catalog, resolve_applicable_policy)
    blocked = planner.execute(PlanTableMaintenanceUseCaseInput(table_uuid="u-1", now=now))
    assert (blocked.status, blocked.operations) == ("planned", ())
    control = planner.execute(PlanTableMaintenanceUseCaseInput(table_uuid="u-2", now=now))
    assert "rewrite_data_files" in [o.operation for o in control.operations]


def test_table_hint_with_new_name_renames_then_signals(hint, tables_repo, rules_repo, catalog, signals, now):
    """A hint with a new table name renames the row and then signals."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("old"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = hint.execute(_hint())
    assert out.action == "renamed"
    assert tables_repo.get(TableId("u-1")).name.table == "orders"
    assert _calls(signals) == [("u-1", "updated", True)]


def test_table_hint_registers_unregistered_table_by_rules(hint, tables_repo, rules_repo, catalog, signals, now):
    """A hint for an unregistered table registers it as managed by the discovery rules."""
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "registered"
    assert tables_repo.get(TableId("u-1")).status == TableStatus.MANAGED
    assert _calls(signals) == [("u-1", "updated", True)]


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
    hint, tables_repo, rules_repo, catalog, discovery_requests, now
):
    """A new uuid under the name of a live row registers it and requests a catalog discovery."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-old", _name("orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-new")
    assert hint.execute(_hint()).action == "registered"
    assert tables_repo.get(TableId("u-new")) is not None
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [("iceberg", None)]


def test_table_hint_fresh_registration_requests_no_discovery(hint, rules_repo, catalog, discovery_requests, now):
    """A fresh registration requests no discovery."""
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    hint.execute(_hint())
    assert discovery_requests.calls == []


def test_table_hint_persists_rename(hint, tables_repo, rules_repo, catalog, log, now):
    """A rename found through a hint is persisted with one update."""
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", _name("old"))
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    hint.execute(_hint())
    assert log == [("tables.update", "u-1")]


def test_table_hint_retry_after_failed_start_still_starts_workflow(
    hint, tables_repo, rules_repo, catalog, signals, now, monkeypatch
):
    """A hint retried after a failed workflow start still signals the workflow."""
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    _fail_first_send(signals, monkeypatch)
    with pytest.raises(RuntimeError):
        hint.execute(_hint())
    assert tables_repo.get(TableId("u-1")) is not None
    assert hint.execute(_hint()).action == "signalled"
    assert _calls(signals) == [("u-1", "updated", True)]
