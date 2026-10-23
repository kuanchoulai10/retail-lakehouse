"""Test the discovery sync and table hint services."""

from __future__ import annotations

from datetime import timedelta

import pytest

from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.model.discovery_rule.table_pattern import TablePattern
from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.maintenance_settings.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)
from application.domain.model.managed_table.managed_table import ManagedTable
from application.domain.model.managed_table.table_name import TableName
from application.domain.model.managed_table.table_selection import TableSelection
from application.domain.model.managed_table.table_status import TableStatus
from application.domain.model.managed_table.table_uuid import TableUuid
from application.domain.model.policy_template.policy_template import PolicyTemplate
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.port.inbound.discovery.process_table_hint import (
    ProcessTableHintUseCaseInput,
)
from application.port.inbound.discovery.sync_discovered_tables import (
    SyncDiscoveredTablesUseCaseInput,
)
from application.exceptions import ConflictError
from application.port.inbound.reconcile.plan_table_maintenance import (
    PlanTableMaintenanceUseCaseInput,
)
from application.port.outbound.catalog.read_catalog import (
    ReadCatalogGatewayObservation,
)
from application.service.discovery.process_table_hint import ProcessTableHintService
from application.service.discovery.sync_discovered_tables import (
    SyncDiscoveredTablesService,
)
from application.service.reconcile.plan_table_maintenance import (
    PlanTableMaintenanceService,
)
from tests.fakes.track_calls import track_calls

TEMPLATE_SETTINGS = MaintenanceSettings(
    rewrite_data_files=RewriteDataFilesSettings(min_reducible_files=9)
)


@pytest.fixture
def template(templates_repo, now):
    t = PolicyTemplate.create(PolicyTemplateId("t-1"), "gold", TEMPLATE_SETTINGS, now)
    templates_repo.create(t)
    return t


def _rule(rules_repo, now, effect, template_id, pattern=TablePattern(), rid="r-1"):
    rules_repo.create(
        DiscoveryRule.create(
            DiscoveryRuleId(rid), 10, effect, pattern, template_id, True, now
        )
    )


def _include_all(rules_repo, now):
    _rule(rules_repo, now, RuleEffect.INCLUDE, PolicyTemplateId("t-1"))


def _row(repo, now, uuid, name, manual=False):
    if manual:
        table = ManagedTable.include_manual(
            TableUuid(uuid), name, PolicyTemplateId("t-1"), MaintenanceSettings(), now
        )
    else:
        table = ManagedTable.register_auto(
            TableUuid(uuid),
            name,
            DiscoveryRuleId("r-1"),
            PolicyTemplateId("t-1"),
            MaintenanceSettings(),
            now,
        )
    repo.create(table)
    return table


@pytest.fixture
def sync(
    tables_repo,
    rules_repo,
    templates_repo,
    discovery_settings_repo,
    catalog,
    signals,
    clock,
):
    return SyncDiscoveredTablesService(
        tables_repo,
        rules_repo,
        templates_repo,
        discovery_settings_repo,
        catalog,
        signals,
        clock=clock,
    )


def _calls(signals):
    return [(c.table_uuid, c.signal, c.start_if_missing) for c in signals.calls]


# --- sync ---


def test_sync_registers_include_match_with_template_copy(
    sync, tables_repo, rules_repo, template, catalog, signals, now
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.renamed, out.dropped, out.skipped) == (1, 0, 0, 0)
    table = tables_repo.get(TableUuid("u-1"))
    assert table.selection == TableSelection.AUTO
    assert table.status == TableStatus.ACTIVE
    assert table.settings == TEMPLATE_SETTINGS
    assert table.source_template_id == PolicyTemplateId("t-1")
    assert table.matched_rule_id == DiscoveryRuleId("r-1")
    assert _calls(signals) == [("u-1", "resume", True)]


def test_sync_exclude_match_and_no_match_register_nothing(
    sync, tables_repo, rules_repo, template, catalog, signals, now
):
    _rule(
        rules_repo,
        now,
        RuleEffect.EXCLUDE,
        None,
        TablePattern(table="tmp_*"),
        rid="r-1",
    )
    catalog.add_table("iceberg", "sales", "tmp_x", "u-1")
    catalog.add_table("iceberg", "sales", "orders", "u-2")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert out.registered == 0
    assert tables_repo.list_all() == []
    assert signals.calls == []


def test_sync_skips_when_discovery_disabled(
    sync,
    tables_repo,
    rules_repo,
    template,
    catalog,
    signals,
    discovery_settings_repo,
    now,
):
    _include_all(rules_repo, now)
    discovery_settings_repo.settings.disable(now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert out.registered == 0
    assert tables_repo.list_all() == []
    assert signals.calls == []


def test_sync_disabled_still_renames_and_drops(
    sync, tables_repo, catalog, signals, discovery_settings_repo, now
):
    discovery_settings_repo.settings.disable(now)
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"))
    _row(tables_repo, now, "u-2", TableName("iceberg", "sales", "gone"))
    catalog.add_table("iceberg", "sales", "new", "u-1")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.renamed, out.dropped) == (0, 1, 1)
    assert tables_repo.get(TableUuid("u-1")).name.table == "new"
    assert tables_repo.get(TableUuid("u-2")).status == TableStatus.DROPPED


def test_sync_skips_table_whose_rule_template_is_missing(
    sync, tables_repo, rules_repo, catalog, now
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    catalog.add_table("iceberg", "sales", "items", "u-2")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.skipped) == (0, 2)
    assert tables_repo.list_all() == []


def test_sync_namespace_scope_never_drops(sync, tables_repo, catalog, signals, now):
    _row(tables_repo, now, "u-in", TableName("iceberg", "sales", "gone"))
    _row(tables_repo, now, "u-other-ns", TableName("iceberg", "hr", "gone"))
    out = sync.execute(
        SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace="sales")
    )
    assert out.dropped == 0
    assert tables_repo.get(TableUuid("u-in")).status == TableStatus.ACTIVE
    assert tables_repo.get(TableUuid("u-other-ns")).status == TableStatus.ACTIVE
    assert signals.calls == []


def test_sync_namespace_scope_still_registers_and_renames(
    sync, tables_repo, rules_repo, template, catalog, now
):
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"))
    catalog.add_table("iceberg", "sales", "new", "u-1")
    catalog.add_table("iceberg", "sales", "fresh", "u-2")
    out = sync.execute(
        SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace="sales")
    )
    assert (out.registered, out.renamed, out.dropped) == (1, 1, 0)


def test_sync_catalog_wide_drops_only_rows_of_that_catalog(
    sync, tables_repo, catalog, signals, now
):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "gone"))
    _row(tables_repo, now, "u-2", TableName("iceberg", "hr", "gone"))
    _row(tables_repo, now, "u-other-cat", TableName("other", "sales", "gone"))
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert out.dropped == 2
    assert tables_repo.get(TableUuid("u-1")).status == TableStatus.DROPPED
    assert tables_repo.get(TableUuid("u-2")).status == TableStatus.DROPPED
    assert tables_repo.get(TableUuid("u-other-cat")).status == TableStatus.ACTIVE
    assert sorted(_calls(signals)) == [("u-1", "stop", False), ("u-2", "stop", False)]


def test_sync_drops_excluded_without_stop_signal_and_ignores_dropped(
    sync, tables_repo, catalog, signals, now
):
    tables_repo.create(
        ManagedTable.exclude_manual(
            TableUuid("u-1"), TableName("iceberg", "sales", "x"), now
        )
    )
    already = _row(tables_repo, now, "u-2", TableName("iceberg", "sales", "y"))
    already.mark_dropped(now)
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert out.dropped == 1
    assert tables_repo.get(TableUuid("u-1")).status == TableStatus.DROPPED
    assert signals.calls == []


def test_sync_dropped_row_whose_uuid_reappears_is_not_renamed_or_revived(
    sync, tables_repo, catalog, signals, now
):
    row = _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"))
    row.mark_dropped(now)
    catalog.add_table("iceberg", "sales", "new", "u-1")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.renamed, out.dropped, out.skipped) == (0, 0, 0, 0)
    stored = tables_repo.get(TableUuid("u-1"))
    assert stored.status == TableStatus.DROPPED
    assert stored.name.table == "old"
    assert signals.calls == []


def test_sync_registers_when_no_discovery_settings_row_exists(
    sync, tables_repo, rules_repo, template, discovery_settings_repo, catalog, now
):
    assert discovery_settings_repo.get_settings().enabled is True
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert out.registered == 1


def test_sync_one_bad_table_is_skipped_not_fatal(
    sync, tables_repo, rules_repo, template, catalog, now, monkeypatch
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "a_bad", "u-bad")
    catalog.add_table("iceberg", "sales", "b_ok", "u-ok")
    original = tables_repo.create

    def create(table):
        if table.id.value == "u-bad":
            raise ConflictError("boom")
        return original(table)

    monkeypatch.setattr(tables_repo, "create", create)
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.skipped) == (1, 1)
    assert tables_repo.get(TableUuid("u-ok")) is not None


def test_sync_persists_rename(sync, tables_repo, catalog, log, now):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"))
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    catalog.add_table("iceberg", "sales", "new", "u-1")
    sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert log == [("tables.update", "u-1")]


def test_sync_rename_keeps_settings(sync, tables_repo, catalog, signals, now):
    table = _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"))
    settings = table.settings
    catalog.add_table("iceberg", "sales", "new", "u-1")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.renamed, out.dropped) == (0, 1, 0)
    assert tables_repo.get(TableUuid("u-1")).name == TableName(
        "iceberg", "sales", "new"
    )
    assert tables_repo.get(TableUuid("u-1")).settings == settings
    assert _calls(signals) == [("u-1", "table_updated", True)]


def test_sync_never_redecides_manual_tables(
    sync, tables_repo, rules_repo, template, catalog, now
):
    _rule(rules_repo, now, RuleEffect.EXCLUDE, None)
    manual = _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"), True)
    auto = _row(tables_repo, now, "u-2", TableName("iceberg", "sales", "auto"))
    catalog.add_table("iceberg", "sales", "new", "u-1")
    catalog.add_table("iceberg", "sales", "auto", "u-2")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.renamed, out.dropped) == (0, 1, 0)
    assert tables_repo.get(manual.id).status == TableStatus.ACTIVE
    assert tables_repo.get(manual.id).name.table == "new"
    assert tables_repo.get(auto.id).status == TableStatus.ACTIVE


# --- table hint ---


@pytest.fixture
def hint(
    tables_repo,
    rules_repo,
    templates_repo,
    discovery_settings_repo,
    catalog,
    signals,
    discovery_requests,
    clock,
):
    return ProcessTableHintService(
        tables_repo,
        rules_repo,
        templates_repo,
        discovery_settings_repo,
        catalog,
        signals,
        discovery_requests,
        clock=clock,
    )


def _hint(table="orders", namespace="sales", event_type="updateTable"):
    return ProcessTableHintUseCaseInput("iceberg", namespace, table, event_type)


def test_table_hint_without_name_requests_namespace_discovery(
    hint, discovery_requests, signals
):
    out = hint.execute(_hint(table=None, event_type="createNamespace"))
    assert out.action == "discovery_requested"
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [
        ("iceberg", "sales")
    ]
    assert signals.calls == []


def test_table_hint_for_registered_table_signals_table_updated(
    hint, tables_repo, catalog, signals, now
):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = hint.execute(_hint())
    assert out.action == "signalled"
    assert _calls(signals) == [("u-1", "table_updated", True)]


def test_table_hint_for_registered_paused_table_still_signals(
    hint, tables_repo, catalog, signals, now
):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "orders")).pause(now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "signalled"
    assert len(signals.calls) == 1


def test_table_hint_for_excluded_registered_table_is_ignored(
    hint, tables_repo, catalog, signals, now
):
    tables_repo.create(
        ManagedTable.exclude_manual(
            TableUuid("u-1"), TableName("iceberg", "sales", "orders"), now
        )
    )
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "ignored"
    assert signals.calls == []


def _busy_observation(uuid):
    return ReadCatalogGatewayObservation(
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


def test_table_hint_for_registered_table_signals_but_cooldown_blocks_replan(
    hint, tables_repo, catalog, signals, now
):
    cooling = _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "orders"))
    for op in MaintenanceOperation.ordered():
        cooling.record_operation_result(op, True, now - timedelta(minutes=1))
    _row(tables_repo, now, "u-2", TableName("iceberg", "sales", "fresh"))
    for uuid, name in (("u-1", "orders"), ("u-2", "fresh")):
        catalog.add_table("iceberg", "sales", name, uuid)
        catalog.observations[("iceberg", "sales", name)] = _busy_observation(uuid)
    assert hint.execute(_hint()).action == "signalled"
    assert _calls(signals) == [("u-1", "table_updated", True)]
    planner = PlanTableMaintenanceService(tables_repo, catalog)
    blocked = planner.execute(PlanTableMaintenanceUseCaseInput("u-1", now))
    assert (blocked.status, blocked.operations) == ("planned", [])
    control = planner.execute(PlanTableMaintenanceUseCaseInput("u-2", now))
    assert "rewrite_data_files" in [o.operation for o in control.operations]


def test_table_hint_with_new_name_renames_then_signals(
    hint, tables_repo, catalog, signals, now
):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = hint.execute(_hint())
    assert out.action == "renamed"
    assert tables_repo.get(TableUuid("u-1")).name.table == "orders"
    assert _calls(signals) == [("u-1", "table_updated", True)]


def test_table_hint_registers_unregistered_table_by_rules(
    hint, tables_repo, rules_repo, template, catalog, signals, now
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "registered"
    assert tables_repo.get(TableUuid("u-1")).selection == TableSelection.AUTO
    assert _calls(signals) == [("u-1", "resume", True)]


def test_table_hint_ignores_unregistered_table_without_match_or_when_disabled(
    hint, tables_repo, rules_repo, template, catalog, discovery_settings_repo, now
):
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "ignored"
    _include_all(rules_repo, now)
    discovery_settings_repo.settings.disable(now)
    assert hint.execute(_hint()).action == "ignored"
    assert tables_repo.list_all() == []


def test_table_hint_for_missing_table_with_row_requests_discovery(
    hint, tables_repo, discovery_requests, now
):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "orders"))
    out = hint.execute(_hint())
    assert out.action == "discovery_requested"
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [
        ("iceberg", None)
    ]


def test_table_hint_for_missing_unknown_table_is_ignored(hint, discovery_requests):
    assert hint.execute(_hint()).action == "ignored"
    assert discovery_requests.calls == []


def test_table_hint_for_dropped_registered_row_is_ignored(
    hint, tables_repo, catalog, signals, now
):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "orders")).mark_dropped(
        now
    )
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "ignored"
    assert signals.calls == []


def test_table_hint_unregistered_with_missing_template_is_ignored(
    hint, tables_repo, rules_repo, catalog, signals, now
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    assert hint.execute(_hint()).action == "ignored"
    assert tables_repo.list_all() == []
    assert signals.calls == []


def test_table_hint_new_uuid_over_live_same_name_row_requests_catalog_discovery(
    hint, tables_repo, rules_repo, template, catalog, discovery_requests, now
):
    _include_all(rules_repo, now)
    _row(tables_repo, now, "u-old", TableName("iceberg", "sales", "orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-new")
    assert hint.execute(_hint()).action == "registered"
    assert tables_repo.get(TableUuid("u-new")) is not None
    assert [(c.catalog, c.namespace) for c in discovery_requests.calls] == [
        ("iceberg", None)
    ]


def test_table_hint_fresh_registration_requests_no_discovery(
    hint, rules_repo, template, catalog, discovery_requests, now
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    hint.execute(_hint())
    assert discovery_requests.calls == []


def test_table_hint_persists_rename(hint, tables_repo, catalog, log, now):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"))
    track_calls(tables_repo, "update", "tables.update", log, lambda t: t.id.value)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    hint.execute(_hint())
    assert log == [("tables.update", "u-1")]


# --- reconcile workflow is (re-)ensured ---


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
    sync, tables_repo, rules_repo, template, catalog, signals, now, monkeypatch
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    _fail_first_send(signals, monkeypatch)
    with pytest.raises(RuntimeError):
        sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert tables_repo.get(TableUuid("u-1")) is not None
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.ensured) == (0, 1)
    assert _calls(signals) == [("u-1", "table_updated", True)]


def test_sync_reensures_workflow_of_every_live_table_that_needs_one(
    sync, tables_repo, catalog, signals, now
):
    _row(tables_repo, now, "u-active", TableName("iceberg", "sales", "a"))
    _row(tables_repo, now, "u-paused", TableName("iceberg", "sales", "p")).pause(now)
    tables_repo.create(
        ManagedTable.exclude_manual(
            TableUuid("u-excluded"), TableName("iceberg", "sales", "x"), now
        )
    )
    _row(
        tables_repo, now, "u-dropped", TableName("iceberg", "sales", "d")
    ).mark_dropped(now)
    for uuid, name in (
        ("u-active", "a"),
        ("u-paused", "p"),
        ("u-excluded", "x"),
        ("u-dropped", "d"),
    ):
        catalog.add_table("iceberg", "sales", name, uuid)
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert out.ensured == 2
    assert sorted(_calls(signals)) == [
        ("u-active", "table_updated", True),
        ("u-paused", "table_updated", True),
    ]


def test_sync_reensures_renamed_table(sync, tables_repo, catalog, signals, now):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "old"))
    catalog.add_table("iceberg", "sales", "new", "u-1")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.renamed, out.ensured) == (1, 1)
    assert _calls(signals) == [("u-1", "table_updated", True)]


def test_sync_does_not_reensure_freshly_registered_table_twice(
    sync, rules_repo, template, catalog, signals, now
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg"))
    assert (out.registered, out.ensured) == (1, 0)
    assert _calls(signals) == [("u-1", "resume", True)]


def test_sync_namespace_scope_does_not_reensure(
    sync, tables_repo, catalog, signals, now
):
    _row(tables_repo, now, "u-1", TableName("iceberg", "sales", "orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    out = sync.execute(
        SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace="sales")
    )
    assert out.ensured == 0
    assert signals.calls == []


def test_table_hint_retry_after_failed_start_still_starts_workflow(
    hint, tables_repo, rules_repo, template, catalog, signals, now, monkeypatch
):
    _include_all(rules_repo, now)
    catalog.add_table("iceberg", "sales", "orders", "u-1")
    _fail_first_send(signals, monkeypatch)
    with pytest.raises(RuntimeError):
        hint.execute(_hint())
    assert tables_repo.get(TableUuid("u-1")) is not None
    assert hint.execute(_hint()).action == "signalled"
    assert _calls(signals) == [("u-1", "table_updated", True)]
