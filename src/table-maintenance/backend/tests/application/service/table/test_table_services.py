"""Test the table use case services."""

from __future__ import annotations

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
from application.domain.model.table.table import Table
from application.domain.model.table.table_name import TableName
from application.domain.model.table.table_status import TableStatus
from application.domain.model.table.table_id import TableId
from application.domain.model.table_maintenance_preset.table_maintenance_preset import (
    TableMaintenancePreset,
)
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)
from application.exceptions import ConflictError, NotFoundError, ValidationError
from application.port.inbound.table.exclude_table import (
    ExcludeTableUseCaseInput,
)
from application.port.inbound.table.get_table import (
    GetTableUseCaseInput,
)
from application.port.inbound.table.include_table import (
    IncludeTableUseCaseInput,
)
from application.port.inbound.table.list_tables import (
    ListTablesUseCaseInput,
)
from application.port.inbound.table.pause_table import (
    PauseTableUseCaseInput,
)
from application.port.inbound.table.reset_table_selection import (
    ResetTableSelectionUseCaseInput,
)
from application.port.inbound.table.resume_table import (
    ResumeTableUseCaseInput,
)
from application.port.inbound.table.trigger_table_maintenance import (
    TriggerTableMaintenanceUseCaseInput,
)
from application.port.inbound.table.update_table_settings import (
    UpdateTableSettingsUseCaseInput,
)
from application.service.maintenance_settings.maintenance_settings_to_dict import (
    maintenance_settings_to_dict,
)
from application.service.table.exclude_table import (
    ExcludeTableService,
)
from application.service.table.get_table import GetTableService
from application.service.table.include_table import (
    IncludeTableService,
)
from application.service.table.list_tables import (
    ListTablesService,
)
from application.service.table.pause_table import (
    PauseTableService,
)
from application.service.table.reset_table_selection import (
    ResetTableSelectionService,
)
from application.service.table.resume_table import (
    ResumeTableService,
)
from application.service.table.trigger_table_maintenance import (
    TriggerTableMaintenanceService,
)
from application.service.table.update_table_settings import (
    UpdateTableSettingsService,
)

NAME = TableName("iceberg", "sales", "orders")
PRESET_SETTINGS = MaintenanceSettings(
    rewrite_data_files=RewriteDataFilesSettings(min_reducible_files=9)
)


@pytest.fixture
def preset(presets_repo, now):
    t = TableMaintenancePreset.create(
        TableMaintenancePresetId("t-1"), "gold", PRESET_SETTINGS, now
    )
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


def _signal(call):
    return (call.table_uuid, call.signal, call.payload, call.start_if_missing)


# --- list / get ---


def test_list_tables_all_and_by_status(tables_repo, now):
    _active(tables_repo, now, "u-1")
    paused = _active(tables_repo, now, "u-2", TableName("iceberg", "sales", "items"))
    paused.pause(now)
    service = ListTablesService(tables_repo)
    assert len(service.execute(ListTablesUseCaseInput()).items) == 2
    out = service.execute(ListTablesUseCaseInput(status="paused"))
    assert [i.uuid for i in out.items] == ["u-2"]
    assert out.items[0].status == "paused"


def test_list_tables_unknown_status_is_invalid(tables_repo):
    with pytest.raises(ValidationError):
        ListTablesService(tables_repo).execute(
            ListTablesUseCaseInput(status="sleeping")
        )


def test_get_table_includes_settings_and_operation_states(tables_repo, now):
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
    with pytest.raises(NotFoundError):
        GetTableService(tables_repo).execute(GetTableUseCaseInput(uuid="nope"))


# --- settings / pause / resume ---


def test_settings_update_signals_workflow(tables_repo, signals, clock, now):
    _active(tables_repo, now, settings=PRESET_SETTINGS)
    out = UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
        UpdateTableSettingsUseCaseInput(
            uuid="u-1", settings={"expire_snapshots": {"retain_last": 2}}
        )
    )
    assert out.settings is not None
    assert out.settings["expire_snapshots"]["retain_last"] == 2
    stored = tables_repo.get(TableId("u-1"))
    assert stored is not None
    assert stored.settings is not None
    assert stored.settings.expire_snapshots.retain_last == 2
    assert stored.settings.rewrite_data_files.min_reducible_files == 5
    assert out.settings["rewrite_data_files"]["min_reducible_files"] == 5
    assert [_signal(c) for c in signals.calls] == [
        ("u-1", "settings_changed", {}, True)
    ]


def test_settings_update_invalid_settings(tables_repo, signals, clock, now):
    _active(tables_repo, now)
    with pytest.raises(ValidationError):
        UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
            UpdateTableSettingsUseCaseInput(uuid="u-1", settings={"x": 1})
        )
    assert signals.calls == []


def test_settings_update_unknown_table(tables_repo, signals, clock):
    with pytest.raises(NotFoundError):
        UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
            UpdateTableSettingsUseCaseInput(uuid="nope", settings={})
        )


def test_settings_update_on_excluded_table_without_settings_conflicts(
    tables_repo, signals, clock, now
):
    _excluded(tables_repo, now)
    with pytest.raises(ConflictError):
        UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
            UpdateTableSettingsUseCaseInput(uuid="u-1", settings={})
        )
    assert signals.calls == []


def test_pause_and_resume_signal_workflow(tables_repo, signals, clock, now):
    _active(tables_repo, now)
    paused = PauseTableService(tables_repo, signals, clock=clock).execute(
        PauseTableUseCaseInput(uuid="u-1")
    )
    assert paused.status == "paused"
    resumed = ResumeTableService(tables_repo, signals, clock=clock).execute(
        ResumeTableUseCaseInput(uuid="u-1")
    )
    assert resumed.status == "active"
    assert [_signal(c) for c in signals.calls] == [
        ("u-1", "pause", {}, False),
        ("u-1", "resume", {}, True),
    ]


def test_pause_excluded_table_conflicts(tables_repo, signals, clock, now):
    _excluded(tables_repo, now)
    with pytest.raises(ConflictError):
        PauseTableService(tables_repo, signals, clock=clock).execute(
            PauseTableUseCaseInput(uuid="u-1")
        )
    assert signals.calls == []


def test_pause_unknown_table(tables_repo, signals, clock):
    with pytest.raises(NotFoundError):
        PauseTableService(tables_repo, signals, clock=clock).execute(
            PauseTableUseCaseInput(uuid="nope")
        )


# --- include ---


def _include_service(tables_repo, presets_repo, catalog, signals, clock):
    return IncludeTableService(tables_repo, presets_repo, catalog, signals, clock=clock)


def _include_input():
    return IncludeTableUseCaseInput(
        catalog="iceberg", namespace="sales", table="orders", preset_id="t-1"
    )


def test_include_new_table_registers_manual_and_starts_workflow(
    tables_repo, presets_repo, preset, catalog, signals, clock
):
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(
        _include_input()
    )
    assert out.uuid == "u-9"
    assert (out.status, out.selection) == ("active", "manual")
    assert out.source_preset_id == "t-1"
    assert out.settings == maintenance_settings_to_dict(preset.settings)
    assert [_signal(c) for c in signals.calls] == [("u-9", "resume", {}, True)]
    assert [c.table_name for c in signals.calls] == ["iceberg.sales.orders"]


def test_include_unknown_table_not_found(
    tables_repo, presets_repo, preset, catalog, signals, clock
):
    with pytest.raises(NotFoundError):
        _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(
            _include_input()
        )
    assert signals.calls == []


def test_include_unknown_preset_not_found(
    tables_repo, presets_repo, catalog, signals, clock
):
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    with pytest.raises(NotFoundError):
        _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(
            _include_input()
        )
    assert tables_repo.list_all() == []


def test_include_reactivates_excluded_table_as_manual(
    tables_repo, presets_repo, preset, catalog, signals, clock, now
):
    _excluded(tables_repo, now, "u-9")
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(
        _include_input()
    )
    assert (out.status, out.selection) == ("active", "manual")
    assert out.settings == maintenance_settings_to_dict(preset.settings)
    assert out.source_preset_id == "t-1"
    assert len(tables_repo.list_all()) == 1
    assert [_signal(c) for c in signals.calls] == [("u-9", "resume", {}, True)]


def test_include_renames_row_when_catalog_name_changed(
    tables_repo, presets_repo, preset, catalog, signals, clock, now
):
    _excluded(tables_repo, now, "u-9", TableName("iceberg", "sales", "old_orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(
        _include_input()
    )
    assert out.table == "orders"


def test_include_dropped_table_conflicts(
    tables_repo, presets_repo, preset, catalog, signals, clock, now
):
    dropped = _dropped(tables_repo, now, "u-9")
    assert dropped.status == TableStatus.DROPPED
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    with pytest.raises(ConflictError):
        _include_service(tables_repo, presets_repo, catalog, signals, clock).execute(
            _include_input()
        )
    assert signals.calls == []


# --- exclude ---


def _exclude_service(tables_repo, catalog, signals, clock):
    return ExcludeTableService(tables_repo, catalog, signals, clock=clock)


def _exclude_input():
    return ExcludeTableUseCaseInput(
        catalog="iceberg", namespace="sales", table="orders"
    )


def test_exclude_registered_table_stops_workflow(
    tables_repo, catalog, signals, clock, now
):
    _active(tables_repo, now, "u-9")
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _exclude_service(tables_repo, catalog, signals, clock).execute(
        _exclude_input()
    )
    assert (out.status, out.selection) == ("excluded", "manual")
    assert out.settings is not None
    assert [_signal(c) for c in signals.calls] == [("u-9", "stop", {}, False)]


def test_exclude_unregistered_table_creates_row_without_settings(
    tables_repo, catalog, signals, clock
):
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _exclude_service(tables_repo, catalog, signals, clock).execute(
        _exclude_input()
    )
    assert (out.uuid, out.status, out.selection) == ("u-9", "excluded", "manual")
    assert out.settings is None
    stored = tables_repo.get(TableId("u-9"))
    assert stored is not None
    assert stored.settings is None
    assert [_signal(c) for c in signals.calls] == [("u-9", "stop", {}, False)]


def test_exclude_table_gone_from_catalog_uses_row_by_name(
    tables_repo, catalog, signals, clock, now
):
    _active(tables_repo, now, "u-9")
    out = _exclude_service(tables_repo, catalog, signals, clock).execute(
        _exclude_input()
    )
    assert out.status == "excluded"
    assert [_signal(c) for c in signals.calls] == [("u-9", "stop", {}, False)]


def test_exclude_unknown_table_not_found(tables_repo, catalog, signals, clock):
    with pytest.raises(NotFoundError):
        _exclude_service(tables_repo, catalog, signals, clock).execute(_exclude_input())
    assert signals.calls == []


def test_exclude_dropped_table_conflicts(tables_repo, catalog, signals, clock, now):
    _dropped(tables_repo, now, "u-9")
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    with pytest.raises(ConflictError):
        _exclude_service(tables_repo, catalog, signals, clock).execute(_exclude_input())
    assert signals.calls == []


def test_exclude_renames_existing_row_to_catalog_name(
    tables_repo, catalog, signals, clock, now
):
    _active(tables_repo, now, "u-9", TableName("iceberg", "sales", "old_orders"))
    catalog.add_table("iceberg", "sales", "orders", "u-9")
    out = _exclude_service(tables_repo, catalog, signals, clock).execute(
        _exclude_input()
    )
    assert (out.table, out.status) == ("orders", "excluded")
    stored = tables_repo.get(TableId("u-9"))
    assert stored is not None
    assert stored.name == NAME


# --- reset selection ---


def _reset_service(tables_repo, rules_repo, presets_repo, signals, clock):
    return ResetTableSelectionService(
        tables_repo, rules_repo, presets_repo, signals, clock=clock
    )


def _rule(rules_repo, now, effect, preset_id, pattern=TablePattern(), rid="r-1"):
    rules_repo.create(
        DiscoveryRule.create(
            DiscoveryRuleId(rid), 10, effect, pattern, preset_id, True, now
        )
    )


def test_reset_selection_applies_matching_include_rule(
    tables_repo, rules_repo, presets_repo, preset, signals, clock, now
):
    _excluded(tables_repo, now)
    _rule(rules_repo, now, RuleEffect.INCLUDE, TableMaintenancePresetId("t-1"))
    out = _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
        ResetTableSelectionUseCaseInput(uuid="u-1")
    )
    assert (out.status, out.selection) == ("active", "auto")
    assert out.matched_rule_id == "r-1"
    assert out.source_preset_id == "t-1"
    assert out.settings == maintenance_settings_to_dict(preset.settings)
    assert [_signal(c) for c in signals.calls] == [("u-1", "resume", {}, True)]


def test_reset_selection_with_missing_rule_preset_not_found(
    tables_repo, rules_repo, presets_repo, signals, clock, now
):
    _excluded(tables_repo, now)
    _rule(rules_repo, now, RuleEffect.INCLUDE, TableMaintenancePresetId("gone"))
    with pytest.raises(NotFoundError):
        _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
            ResetTableSelectionUseCaseInput(uuid="u-1")
        )
    assert signals.calls == []


def test_reset_selection_with_exclude_rule_stops_workflow(
    tables_repo, rules_repo, presets_repo, signals, clock, now
):
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
    assert [_signal(c) for c in signals.calls] == [("u-1", "stop", {}, False)]


def test_reset_selection_without_matching_rule_excludes(
    tables_repo, rules_repo, presets_repo, signals, clock, now
):
    _active(tables_repo, now)
    out = _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
        ResetTableSelectionUseCaseInput(uuid="u-1")
    )
    assert (out.status, out.matched_rule_id) == ("excluded", None)
    assert [_signal(c) for c in signals.calls] == [("u-1", "stop", {}, False)]


def test_reset_selection_unknown_table(
    tables_repo, rules_repo, presets_repo, signals, clock
):
    with pytest.raises(NotFoundError):
        _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
            ResetTableSelectionUseCaseInput(uuid="nope")
        )


def test_reset_selection_dropped_table_conflicts(
    tables_repo, rules_repo, presets_repo, signals, clock, now
):
    _dropped(tables_repo, now)
    with pytest.raises(ConflictError):
        _reset_service(tables_repo, rules_repo, presets_repo, signals, clock).execute(
            ResetTableSelectionUseCaseInput(uuid="u-1")
        )
    assert signals.calls == []


# --- trigger ---


def test_trigger_signals_operations_in_canonical_order(tables_repo, signals, now):
    _active(tables_repo, now)
    out = TriggerTableMaintenanceService(tables_repo, signals).execute(
        TriggerTableMaintenanceUseCaseInput(
            uuid="u-1",
            operations=["expire_snapshots", "rewrite_data_files", "expire_snapshots"],
        )
    )
    assert out.accepted is True
    assert [_signal(c) for c in signals.calls] == [
        (
            "u-1",
            "trigger_now",
            {"operations": ["rewrite_data_files", "expire_snapshots"]},
            True,
        )
    ]


def test_trigger_on_dropped_table_conflicts(tables_repo, signals, now):
    _dropped(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(
                uuid="u-1", operations=["rewrite_data_files"]
            )
        )
    assert signals.calls == []


def test_trigger_on_excluded_table_conflicts(tables_repo, signals, now):
    _excluded(tables_repo, now)
    with pytest.raises(ConflictError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(
                uuid="u-1", operations=["rewrite_data_files"]
            )
        )


@pytest.mark.parametrize("operations", [[], ["defrag"]])
def test_trigger_invalid_operations(tables_repo, signals, now, operations):
    _active(tables_repo, now)
    with pytest.raises(ValidationError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(uuid="u-1", operations=operations)
        )
    assert signals.calls == []


def test_trigger_unknown_table(tables_repo, signals):
    with pytest.raises(NotFoundError):
        TriggerTableMaintenanceService(tables_repo, signals).execute(
            TriggerTableMaintenanceUseCaseInput(
                uuid="nope", operations=["rewrite_data_files"]
            )
        )


def test_settings_update_on_paused_table_starts_workflow_if_missing(
    tables_repo, signals, clock, now
):
    _active(tables_repo, now).pause(now)
    UpdateTableSettingsService(tables_repo, signals, clock=clock).execute(
        UpdateTableSettingsUseCaseInput(uuid="u-1", settings={})
    )
    assert [_signal(c) for c in signals.calls] == [
        ("u-1", "settings_changed", {}, True)
    ]
