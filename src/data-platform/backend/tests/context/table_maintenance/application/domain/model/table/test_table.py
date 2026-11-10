"""Test the Table aggregate: factories, lifecycle transitions, selection and operation state."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
    MaintenanceSettings,
)
from context.table_maintenance.application.domain.model.table import (
    InvalidTableTransition,
    OperationState,
    Table,
    TableId,
    TableName,
    TableSelection,
    TableStatus,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
NAME = TableName(catalog="iceberg", namespace="inventory", table="orders")
RULE = TableDiscoveryRuleId("r1")
PRESET = TableMaintenancePresetId("t1")
SETTINGS = MaintenanceSettings()
OP = MaintenanceOperation.REWRITE_DATA_FILES


def auto() -> Table:
    """Provide an active table that was registered automatically through a rule."""
    return Table.register_auto(TableId("u1"), NAME, RULE, PRESET, SETTINGS, T0)


def manual() -> Table:
    """Provide an active table that was included manually."""
    return Table.include_manual(TableId("u1"), NAME, PRESET, SETTINGS, T0)


def excluded() -> Table:
    """Provide a table that was excluded manually."""
    return Table.exclude_manual(TableId("u1"), NAME, T0)


def test_factories():
    """The auto factory yields an active auto table linked to its rule and preset."""
    a = auto()
    assert (a.status, a.selection) == (TableStatus.ACTIVE, TableSelection.AUTO)
    assert a.matched_rule_id == RULE and a.source_preset_id == PRESET
    assert a.registered_at == a.updated_at == T0
    m = manual()
    assert (m.status, m.selection) == (TableStatus.ACTIVE, TableSelection.MANUAL)
    assert m.matched_rule_id is None


def test_dropped_is_terminal():
    """A dropped table cannot change status again."""
    t = auto()
    t.mark_dropped(T1)
    t.mark_dropped(T1)
    assert t.status == TableStatus.DROPPED
    commands = [
        lambda: t.pause(T1),
        lambda: t.resume(T1),
        lambda: t.exclude(T1),
        lambda: t.rename(NAME, T1),
        lambda: t.reset_to_auto(T1),
        lambda: t.apply_auto_decision(RULE, PRESET, SETTINGS, T1),
        lambda: t.update_settings(SETTINGS, T1),
        lambda: t.include_manually(PRESET, SETTINGS, T1),
        lambda: t.record_operation_result(OP, True, T1),
    ]
    for command in commands:
        with pytest.raises(InvalidTableTransition):
            command()


def test_pause_resume_only_from_active_paused():
    """Pausing needs an active table and resuming needs a paused one."""
    t = excluded()
    with pytest.raises(InvalidTableTransition):
        t.pause(T1)
    with pytest.raises(InvalidTableTransition):
        t.resume(T1)
    a = auto()
    a.resume(T1)
    assert a.status == TableStatus.ACTIVE
    a.pause(T1)
    assert a.status == TableStatus.PAUSED and a.updated_at == T1
    a.resume(T1)
    assert a.status == TableStatus.ACTIVE


def test_exclude_manual_has_no_settings_and_no_workflow():
    """A manually excluded table has no settings and is not enrolled."""
    t = excluded()
    assert t.is_enrolled is False
    assert t.settings is None
    assert t.selection == TableSelection.MANUAL
    assert t.status == TableStatus.EXCLUDED


def test_exclude_sets_manual():
    """Excluding a table makes it excluded with a manual selection."""
    t = auto()
    t.exclude(T1)
    assert (t.status, t.selection) == (TableStatus.EXCLUDED, TableSelection.MANUAL)


def test_is_enrolled_when_active_or_paused():
    """An active or paused table is enrolled."""
    t = auto()
    assert t.is_enrolled
    t.pause(T1)
    assert t.is_enrolled


def test_reset_to_auto_then_apply_include_decision():
    """After a reset to auto, an include decision makes the table active with the settings."""
    t = excluded()
    t.reset_to_auto(T1)
    assert t.selection == TableSelection.AUTO
    t.apply_auto_decision(RULE, PRESET, SETTINGS, T1)
    assert t.status == TableStatus.ACTIVE
    assert t.settings == SETTINGS
    assert t.selection == TableSelection.AUTO
    assert t.matched_rule_id == RULE and t.source_preset_id == PRESET


def test_apply_include_keeps_existing_settings():
    """An include decision keeps the settings the table already has."""
    t = auto()
    own = MaintenanceSettings(reconcile_interval=timedelta(hours=2))
    t.update_settings(own, T1)
    t.apply_auto_decision(RULE, PRESET, SETTINGS, T1)
    assert t.settings == own


def test_apply_auto_decision_without_rule_excludes_auto_table():
    """An auto decision with no matching rule excludes an auto table and keeps its settings."""
    t = auto()
    t.apply_auto_decision(None, None, None, T1)
    assert t.status == TableStatus.EXCLUDED
    assert t.settings == SETTINGS
    assert t.selection == TableSelection.AUTO


def test_apply_exclude_rule_excludes_auto_table():
    """An exclude rule excludes an auto table and records the rule."""
    t = auto()
    t.apply_auto_decision(TableDiscoveryRuleId("r2"), None, None, T1)
    assert t.status == TableStatus.EXCLUDED
    assert t.matched_rule_id == TableDiscoveryRuleId("r2")


def test_apply_auto_decision_ignored_for_manual():
    """An auto decision does not change a manually selected table."""
    t = manual()
    t.apply_auto_decision(None, None, None, T1)
    assert t.status == TableStatus.ACTIVE
    assert t.updated_at == T0


def test_update_settings_requires_settings_capable_status():
    """Settings can only be updated on a table whose status allows settings."""
    t = excluded()
    with pytest.raises(InvalidTableTransition):
        t.update_settings(SETTINGS, T1)
    a = auto()
    new = MaintenanceSettings(reconcile_interval=timedelta(hours=3))
    a.update_settings(new, T1)
    assert a.settings == new and a.updated_at == T1


def test_include_manually_reactivates_excluded_table():
    """Including an excluded table manually makes it active with the given settings and preset."""
    t = excluded()
    t.include_manually(PRESET, SETTINGS, T1)
    assert (t.status, t.selection) == (TableStatus.ACTIVE, TableSelection.MANUAL)
    assert t.settings == SETTINGS
    assert t.source_preset_id == PRESET
    assert t.matched_rule_id is None


def test_include_manually_from_paused_auto_table():
    """Including a paused auto table manually makes it active, manual and without a rule."""
    t = auto()
    t.pause(T1)
    t.include_manually(PRESET, SETTINGS, T1)
    assert t.status == TableStatus.ACTIVE
    assert t.selection == TableSelection.MANUAL
    assert t.matched_rule_id is None


def test_backoff_doubles_and_caps():
    """The cooldown doubles with each consecutive failure up to a cap."""
    base = timedelta(hours=1)
    for failures, expected in [(0, 1), (1, 2), (3, 8), (10, 24)]:
        s = OperationState(consecutive_failures=failures)
        assert s.effective_cooldown(base) == timedelta(hours=expected)
    assert OperationState(consecutive_failures=2).effective_cooldown(timedelta(hours=30)) == timedelta(hours=30)
    failed = OperationState().after_failure(T0).after_failure(T1)
    assert failed.consecutive_failures == 2 and failed.last_attempt_at == T1
    ok = failed.after_success(T1)
    assert ok.consecutive_failures == 0 and ok.last_attempt_at == T1


def test_record_operation_result():
    """A failure raises the failure count and a success resets it."""
    t = auto()
    assert t.operation_state(OP) == OperationState()
    t.record_operation_result(OP, False, T1)
    assert t.operation_state(OP).consecutive_failures == 1
    t.pause(T1)
    t.record_operation_result(OP, True, T1)
    assert t.operation_state(OP).consecutive_failures == 0
    assert t.updated_at == T1


def test_rename_keeps_identity():
    """Renaming a table keeps its id and equals the original."""
    t = auto()
    new = TableName(catalog="iceberg", namespace="inventory", table="orders_v2")
    t.rename(new, T1)
    assert t.id == TableId("u1") and t.name == new
    assert t == auto()


def test_apply_auto_include_keeps_paused_table_paused():
    """An auto include decision keeps a paused table paused."""
    t = auto()
    t.pause(T1)
    t.apply_auto_decision(RULE, PRESET, SETTINGS, T1)
    assert t.status == TableStatus.PAUSED


def test_apply_auto_include_without_settings_raises_when_table_has_none():
    """An auto include decision for a table without settings raises an invalid transition."""
    t = excluded()
    t.reset_to_auto(T1)
    with pytest.raises(InvalidTableTransition):
        t.apply_auto_decision(RULE, PRESET, None, T1)
    assert t.status == TableStatus.EXCLUDED
    assert t.settings is None


def test_apply_auto_include_keeps_source_preset_when_settings_kept():
    """An auto include decision that keeps settings keeps the source preset and the rule."""
    t = auto()
    t.apply_auto_decision(RULE, TableMaintenancePresetId("t2"), SETTINGS, T1)
    assert t.source_preset_id == PRESET
    assert t.matched_rule_id == RULE


def test_table_rejects_wrong_type_on_assignment():
    """Every assignment is validated: a string is not a datetime."""
    t = auto()
    with pytest.raises(ValidationError):
        t.updated_at = "2026-01-01T00:00:00Z"  # ty: ignore[invalid-assignment]
    assert t.updated_at == T0


def test_table_name_rejects_an_empty_table_as_a_validation_error():
    """An empty table name is a broken invariant at construction."""
    with pytest.raises(ValidationError, match="table name must not be empty"):
        TableName(catalog="iceberg", namespace="inventory", table="")


def test_operation_state_is_immutable():
    """An operation state changes only by building a new one."""
    state = OperationState()
    with pytest.raises(ValidationError):
        state.consecutive_failures = 1


def test_table_equality_follows_identity():
    """Two tables with one id are equal even when their state differs."""
    a, b = auto(), auto()
    b.pause(T1)
    assert a == b and hash(a) == hash(b)
