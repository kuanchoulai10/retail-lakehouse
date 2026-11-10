"""Test the table use case services."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    MaintenanceSettings,
    RewriteDataFilesSettings,
)
from context.table_maintenance.application.domain.model.table import (
    Table,
    TableId,
    TableName,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePreset,
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table import (
    ExcludeTableUseCaseInput,
    GetTableUseCaseInput,
    IncludeTableUseCaseInput,
    ListTablesUseCaseInput,
    PauseTableUseCaseInput,
    ResetTableSelectionUseCaseInput,
    ResumeTableUseCaseInput,
    TriggerTableMaintenanceUseCaseInput,
    TriggerTableReconciliationUseCaseInput,
    UpdateTableSettingsUseCaseInput,
)
from context.table_maintenance.application.service.table import (
    ExcludeTableService,
    GetTableService,
    IncludeTableService,
    ListTablesService,
    PauseTableService,
    ResetTableSelectionService,
    ResumeTableService,
    TriggerTableMaintenanceService,
    TriggerTableReconciliationService,
    UpdateTableSettingsService,
)

NAME = TableName("iceberg", "sales", "orders")
PRESET_SETTINGS = MaintenanceSettings(rewrite_data_files=RewriteDataFilesSettings(min_reducible_files=9))


@pytest.fixture
def preset(presets_repo, now):
    """Provide a stored preset."""
    t = TableMaintenancePreset.create(TableMaintenancePresetId("t-1"), "gold", PRESET_SETTINGS, now)
    presets_repo.create(t)
    return t


def _active(repo, now, uuid="u-1", name=NAME, settings=None):
    table = Table.include_manual(
        TableId(uuid),
        name,
        TableMaintenancePresetId("t-1"),
        settings or MaintenanceSettings(),
        now,
    )
    repo.create(table)
    return table


def _excluded(repo, now, uuid="u-1", name=NAME):
    table = Table.exclude_manual(TableId(uuid), name, now)
    repo.create(table)
    return table


def _dropped(repo, now, uuid="u-1", name=NAME):
    table = _active(repo, now, uuid, name)
    table.mark_dropped(now)
    return table


def _change(call):
    return (call.table_uuid, call.change, call.operations, call.is_enrolled)


# --- list / get ---


def test_list_tables_all_and_by_status(tables_repo, now):
    """Listing returns all tables, or only those of the requested status."""
    _active(tables_repo, now, "u-1")
    paused = _active(tables_repo, now, "u-2", TableName("iceberg", "sales", "items"))
    paused.pause(now)
    service = ListTablesService(tables_repo)
    assert len(service.execute(ListTablesUseCaseInput()).items) == 2
    out = service.execute(ListTablesUseCaseInput(status="paused"))
    assert [i.uuid for i in out.items] == ["u-2"]
    assert out.items[0].status == "paused"


def test_list_tables_unknown_status_is_invalid(tables_repo):
    """Listing with an unknown status raises a ValidationError."""
    with pytest.raises(ValidationError):
        ListTablesService(tables_repo).execute(ListTablesUseCaseInput(status="sleeping"))


def test_get_table_includes_settings_and_operation_states(tables_repo, now):
    """Getting a table returns its name, status, selection, settings and operation states."""
    table = _active(tables_repo, now)
    table.record_operation_result(MaintenanceOperation.EXPIRE_SNAPSHOTS, False, now)
    out = GetTableService(tables_repo).execute(GetTableUseCaseInput(uuid="u-1"))
    assert (out.catalog, out.namespace, out.table) == ("iceberg", "sales", "orders")
    assert out.status == "active"
    assert out.selection == "manual"
    assert out.settings is not None
    assert out.settings["reconcile_interval_seconds"] == 3600
    assert out.source_preset_id == "t-1"
    assert out.operation_states["expire_snapshots"] == {
        "last_attempt_at": now,
        "consecutive_failures": 1,
    }


def test_get_unknown_table_not_found(tables_repo):
    """Getting an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        GetTableService(tables_repo).execute(GetTableUseCaseInput(uuid="nope"))


# --- settings / pause / resume ---


def test_settings_update_signals_workflow(tables_repo, signals, clock, now):
    """A settings update is stored and signalled to the workflow."""
    _active(tables_repo, now, settings=PRESET_SETTINGS)
    out = UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
        UpdateTableSettingsUseCaseInput(uuid="u-1", settings={"expire_snapshots": {"retain_last": 2}})
    )
    assert out.settings is not None
    assert out.settings["expire_snapshots"]["retain_last"] == 2
    stored = tables_repo.get(TableId("u-1"))
    assert stored is not None
    assert stored.settings is not None
    assert stored.settings.expire_snapshots.retain_last == 2
    assert stored.settings.rewrite_data_files.min_reducible_files == 5
    assert out.settings["rewrite_data_files"]["min_reducible_files"] == 5
    assert [_change(c) for c in signals.calls] == [("u-1", "settings_changed", [], True)]


def test_settings_update_invalid_settings(tables_repo, signals, clock, now):
    """Invalid settings are rejected and nothing is signalled."""
    _active(tables_repo, now)
    with pytest.raises(ValidationError):
        UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
            UpdateTableSettingsUseCaseInput(uuid="u-1", settings={"x": 1})
        )
    assert signals.calls == []


def test_settings_update_unknown_table(tables_repo, signals, clock):
    """A settings update for an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
            UpdateTableSettingsUseCaseInput(uuid="nope", settings={})
        )


def test_settings_update_on_excluded_table_without_settings_conflicts(tables_repo, signals, clock, now):
    """A settings update for an excluded table without settings raises ConflictError."""
    _excluded(tables_repo, now)
    with pytest.raises(ConflictError):
        UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
            UpdateTableSettingsUseCaseInput(uuid="u-1", settings={})
        )
    assert signals.calls == []


def test_pause_and_resume_signal_workflow(tables_repo, signals, clock, now):
    """Pausing and resuming change the status and signal the workflow."""
    _active(tables_repo, now)
    paused = PauseTableService(tables_repo, signals, clock=clock).execute(PauseTableUseCaseInput(uuid="u-1"))
    assert paused.status == "paused"
    resumed = ResumeTableService(tables_repo, signals, clock=clock).execute(ResumeTableUseCaseInput(uuid="u-1"))
    assert resumed.status == "active"
    assert [_change(c) for c in signals.calls] == [
        ("u-1", "paused", [], True),
        ("u-1", "resumed", [], True),
    ]


def test_pause_excluded_table_conflicts(tables_repo, signals, clock, now):
    """Pausing an excluded table raises ConflictError."""
    _excluded(tables_repo, now)
    with pytest.raises(ConflictError):
        PauseTableService(tables_repo, signals, clock=clock).execute(PauseTableUseCaseInput(uuid="u-1"))
    assert signals.calls == []


def test_pause_unknown_table(tables_repo, signals, clock):
    """Pausing an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        PauseTableService(tables_repo, signals, clock=clock).execute(PauseTableUseCaseInput(uuid="nope"))


# --- include ---


def _include_service(tables_repo, presets_repo, catalog, signals, clock):
    return IncludeTableService(tables_repo, presets_repo, catalog, signals, clock=clock)


def _include_input():
    return IncludeTableUseCaseInput(catalog="iceberg", namespace="sales", table="orders", preset_id="t-1")


def test_include_new_table_registers_manual_and_starts_workflow(
    tables_repo, presets_repo, preset, catalog, signals, clock
):
    """Including a new table registers it as manual and starts its workflow."""
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(_include_input())
    assert out.uuid == "u-9"
    assert (out.status, out.selection) == ("active", "manual")
    assert out.source_preset_id == "t-1"
    assert out.settings == preset.settings.to_primitives()
    assert [_change(c) for c in signals.calls] == [("u-9", "resumed", [], True)]
    assert [c.table_name for c in signals.calls] == ["iceberg.sales.orders"]


def test_include_unknown_table_not_found(tables_repo, presets_repo, preset, catalog, signals, clock):
    """Including a table that is not in the catalog raises NotFoundError."""
    with pytest.raises(NotFoundError):
        _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(_include_input())
    assert signals.calls == []


def test_include_unknown_preset_not_found(tables_repo, presets_repo, catalog, signals, clock):
    """Including a table with an unknown preset raises NotFoundError."""
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    with pytest.raises(NotFoundError):
        _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(_include_input())
    assert tables_repo.list_all() == []


def test_include_reactivates_excluded_table_as_manual(tables_repo, presets_repo, preset, catalog, signals, clock, now):
    """Including an excluded table activates it as manual with the preset settings."""
    _excluded(tables_repo, now, "u-9")
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(_include_input())
    assert (out.status, out.selection) == ("active", "manual")
    assert out.settings == preset.settings.to_primitives()
    assert out.source_preset_id == "t-1"
    assert len(tables_repo.list_all()) == 1
    assert [_change(c) for c in signals.calls] == [("u-9", "resumed", [], True)]


def test_include_renames_row_when_catalog_name_changed(tables_repo, presets_repo, preset, catalog, signals, clock, now):
    """Including a table renames its row when the catalog name changed."""
    _excluded(tables_repo, now, "u-9", TableName("iceberg", "sales", "old_orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(_include_input())
    assert out.table == "orders"


def test_include_dropped_table_conflicts(tables_repo, presets_repo, preset, catalog, signals, clock, now):
    """Including a dropped table raises ConflictError."""
    dropped = _dropped(tables_repo, now, "u-9")
    assert dropped.status == TableStatus.DROPPED
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    with pytest.raises(ConflictError):
        _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(_include_input())
    assert signals.calls == []


# --- exclude ---


def _exclude_service(tables_repo, catalog, signals, clock):
    return ExcludeTableService(tables_repo, catalog, signals, clock=clock)


def _exclude_input():
    return ExcludeTableUseCaseInput(catalog="iceberg", namespace="sales", table="orders")


def test_exclude_registered_table_stops_workflow(tables_repo, catalog, signals, clock, now):
    """Excluding a registered table makes it excluded and stops its workflow."""
    _active(tables_repo, now, "u-9")
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _exclude_service(tables_repo, catalog, signals, clock).execute(_exclude_input())
    assert (out.status, out.selection) == ("excluded", "manual")
    assert out.settings is not None
    assert [_change(c) for c in signals.calls] == [("u-9", "stopped", [], False)]


def test_exclude_unregistered_table_creates_row_without_settings(tables_repo, catalog, signals, clock):
    """Excluding an unregistered table creates an excluded row without settings."""
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _exclude_service(tables_repo, catalog, signals, clock).execute(_exclude_input())
    assert (out.uuid, out.status, out.selection) == ("u-9", "excluded", "manual")
    assert out.settings is None
    stored = tables_repo.get(TableId("u-9"))
    assert stored is not None
    assert stored.settings is None
    assert [_change(c) for c in signals.calls] == [("u-9", "stopped", [], False)]


def test_exclude_table_gone_from_catalog_uses_row_by_name(tables_repo, catalog, signals, clock, now):
    """Excluding a table gone from the catalog finds its row by name."""
    _active(tables_repo, now, "u-9")
    out = _exclude_service(tables_repo, catalog, signals, clock).execute(_exclude_input())
    assert out.status == "excluded"
    assert [_change(c) for c in signals.calls] == [("u-9", "stopped", [], False)]


def test_exclude_unknown_table_not_found(tables_repo, catalog, signals, clock):
    """Excluding a table that is neither stored nor in the catalog raises NotFoundError."""
    with pytest.raises(NotFoundError):
        _exclude_service(tables_repo, catalog, signals, clock).execute(_exclude_input())
    assert signals.calls == []


def test_exclude_dropped_table_conflicts(tables_repo, catalog, signals, clock, now):
    """Excluding a dropped table raises ConflictError."""
    _dropped(tables_repo, now, "u-9")
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    with pytest.raises(ConflictError):
        _exclude_service(tables_repo, catalog, signals, clock).execute(_exclude_input())
    assert signals.calls == []


def test_exclude_renames_existing_row_to_catalog_name(tables_repo, catalog, signals, clock, now):
    """Excluding a table renames its row to the catalog name."""
    _active(tables_repo, now, "u-9", TableName("iceberg", "sales", "old_orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _exclude_service(tables_repo, catalog, signals, clock).execute(_exclude_input())
    assert (out.table, out.status) == ("orders", "excluded")
    stored = tables_repo.get(TableId("u-9"))
    assert stored is not None
    assert stored.name == NAME


# --- reset selection ---


def _reset_service(tables_repo, rules_repo, presets_repo, signals, clock):
    return ResetTableSelectionService(tables_repo, rules_repo, presets_repo, signals, clock=clock)


DEFAULT_PATTERN = TablePattern()


def _rule(rules_repo, now, effect, preset_id, pattern=DEFAULT_PATTERN, rid="r-1"):
    rules_repo.create(TableDiscoveryRule.create(TableDiscoveryRuleId(rid), 10, effect, pattern, preset_id, True, now))


def test_reset_selection_applies_matching_include_rule(
    tables_repo, rules_repo, presets_repo, preset, signals, clock, now
):
    """Resetting the selection applies the matching include rule and its preset."""
    _excluded(tables_repo, now)
    _rule(rules_repo, now, RuleEffect.INCLUDE, TableMaintenancePresetId("t-1"))
    out = _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
        ResetTableSelectionUseCaseInput(uuid="u-1")
    )
    assert (out.status, out.selection) == ("active", "auto")
    assert out.matched_rule_id == "r-1"
    assert out.source_preset_id == "t-1"
    assert out.settings == preset.settings.to_primitives()
    assert [_change(c) for c in signals.calls] == [("u-1", "resumed", [], True)]


def test_reset_selection_with_missing_rule_preset_not_found(tables_repo, rules_repo, presets_repo, signals, clock, now):
    """Resetting the selection when the rule preset is missing raises NotFoundError."""
    _excluded(tables_repo, now)
    _rule(rules_repo, now, RuleEffect.INCLUDE, TableMaintenancePresetId("gone"))
    with pytest.raises(NotFoundError):
        _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
            ResetTableSelectionUseCaseInput(uuid="u-1")
        )
    assert signals.calls == []


def test_reset_selection_with_exclude_rule_stops_workflow(tables_repo, rules_repo, presets_repo, signals, clock, now):
    """Resetting the selection with a matching exclude rule excludes the table and stops its workflow."""
    _active(tables_repo, now)
    _rule(rules_repo, now, RuleEffect.EXCLUDE, None)
    out = _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
        ResetTableSelectionUseCaseInput(uuid="u-1")
    )
    assert (out.status, out.selection, out.matched_rule_id) == (
        "excluded",
        "auto",
        "r-1",
    )
    assert [_change(c) for c in signals.calls] == [("u-1", "stopped", [], False)]


def test_reset_selection_without_matching_rule_excludes(tables_repo, rules_repo, presets_repo, signals, clock, now):
    """Resetting the selection with no matching rule excludes the table."""
    _active(tables_repo, now)
    out = _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
        ResetTableSelectionUseCaseInput(uuid="u-1")
    )
    assert (out.status, out.matched_rule_id) == ("excluded", None)
    assert [_change(c) for c in signals.calls] == [("u-1", "stopped", [], False)]


def test_reset_selection_unknown_table(tables_repo, rules_repo, presets_repo, signals, clock):
    """Resetting the selection of an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
            ResetTableSelectionUseCaseInput(uuid="nope")
        )


def test_reset_selection_dropped_table_conflicts(tables_repo, rules_repo, presets_repo, signals, clock, now):
    """Resetting the selection of a dropped table raises ConflictError."""
    _dropped(tables_repo, now)
    with pytest.raises(ConflictError):
        _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
            ResetTableSelectionUseCaseInput(uuid="u-1")
        )
    assert signals.calls == []


# --- trigger ---


def test_trigger_signals_operations_in_canonical_order(tables_repo, signals, now):
    """Triggering signals the requested operations in canonical order."""
    _active(tables_repo, now)
    out = TriggerTableMaintenanceService(tables_repo, signals).execute(
        TriggerTableMaintenanceUseCaseInput(
            uuid="u-1",
            operations=["expire_snapshots", "rewrite_data_files", "expire_snapshots"],
        )
    )
    assert out.accepted is True
    assert [_change(c) for c in signals.calls] == [
        (
            "u-1",
            "maintenance_requested",
            ["rewrite_data_files", "expire_snapshots"],
            True,
        )
    ]


def test_trigger_on_dropped_table_conflicts(tables_repo, signals, now):
    """Triggering maintenance on a dropped table raises ConflictError."""
    _dropped(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=["rewrite_data_files"])
        )
    assert signals.calls == []


def test_trigger_on_excluded_table_conflicts(tables_repo, signals, now):
    """Triggering maintenance on an excluded table raises ConflictError."""
    _excluded(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=["rewrite_data_files"])
        )


@pytest.mark.parametrize("operations", [[], ["defrag"]])
def test_trigger_invalid_operations(tables_repo, signals, now, operations):
    """Invalid operations are rejected and nothing is signalled."""
    _active(tables_repo, now)
    with pytest.raises(ValidationError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=operations)
        )
    assert signals.calls == []


def test_trigger_unknown_table(tables_repo, signals):
    """Triggering maintenance on an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="nope", operations=["rewrite_data_files"])
        )


# --- reconcile now ---


def test_reconcile_now_signals_the_workflow(tables_repo, signals, now):
    """Reconciling now sends a reconcile request to the table's workflow."""
    _active(tables_repo, now)
    out = TriggerTableReconciliationService(tables_repo, signals).execute(
        TriggerTableReconciliationUseCaseInput(uuid="u-1")
    )
    assert out.accepted is True
    assert [_change(c) for c in signals.calls] == [("u-1", "reconcile_requested", [], True)]


def test_reconcile_now_on_paused_table_is_accepted(tables_repo, signals, now):
    """A paused table is still enrolled, so its reconciliation records the pause."""
    _active(tables_repo, now).pause(now)
    TriggerTableReconciliationService(tables_repo, signals).execute(TriggerTableReconciliationUseCaseInput(uuid="u-1"))
    assert [_change(c) for c in signals.calls] == [("u-1", "reconcile_requested", [], True)]


@pytest.mark.parametrize("make", [_excluded, _dropped], ids=["excluded", "dropped"])
def test_reconcile_now_on_table_out_of_maintenance_conflicts(tables_repo, signals, now, make):
    """Reconciling a table that is not enrolled raises ConflictError and signals nothing."""
    make(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableReconciliationService(tables_repo, signals).execute(
            TriggerTableReconciliationUseCaseInput(uuid="u-1")
        )
    assert signals.calls == []


def test_reconcile_now_unknown_table(tables_repo, signals):
    """Reconciling an unknown table raises NotFoundError."""
    with pytest.raises(NotFoundError):
        TriggerTableReconciliationService(tables_repo, signals).execute(
            TriggerTableReconciliationUseCaseInput(uuid="nope")
        )
    assert signals.calls == []


def test_settings_update_on_paused_table_starts_workflow_if_missing(tables_repo, signals, clock, now):
    """A settings update on a paused table asks for the workflow to be started if it is missing."""
    _active(tables_repo, now).pause(now)
    UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
        UpdateTableSettingsUseCaseInput(uuid="u-1", settings={})
    )
    assert [_change(c) for c in signals.calls] == [("u-1", "settings_changed", [], True)]
