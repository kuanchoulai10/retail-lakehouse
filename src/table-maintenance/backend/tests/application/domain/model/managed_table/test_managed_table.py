from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from application.domain.model.discovery_rule import DiscoveryRuleId
from application.domain.model.maintenance import MaintenanceOperation
from application.domain.model.maintenance_settings import MaintenanceSettings
from application.domain.model.managed_table import (
    InvalidTableTransition,
    ManagedTable,
    OperationState,
    TableName,
    TableSelection,
    TableStatus,
    TableUuid,
)
from application.domain.model.policy_template import PolicyTemplateId

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
NAME = TableName(catalog="iceberg", namespace="inventory", table="orders")
RULE = DiscoveryRuleId("r1")
TEMPLATE = PolicyTemplateId("t1")
SETTINGS = MaintenanceSettings()
OP = MaintenanceOperation.REWRITE_DATA_FILES


def auto() -> ManagedTable:
    return ManagedTable.register_auto(
        TableUuid("u1"), NAME, RULE, TEMPLATE, SETTINGS, T0
    )


def manual() -> ManagedTable:
    return ManagedTable.include_manual(TableUuid("u1"), NAME, TEMPLATE, SETTINGS, T0)


def excluded() -> ManagedTable:
    return ManagedTable.exclude_manual(TableUuid("u1"), NAME, T0)


def test_factories():
    a = auto()
    assert (a.status, a.selection) == (TableStatus.ACTIVE, TableSelection.AUTO)
    assert a.matched_rule_id == RULE and a.source_template_id == TEMPLATE
    assert a.registered_at == a.updated_at == T0
    m = manual()
    assert (m.status, m.selection) == (TableStatus.ACTIVE, TableSelection.MANUAL)
    assert m.matched_rule_id is None


def test_dropped_is_terminal():
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
        lambda: t.apply_auto_decision(RULE, TEMPLATE, SETTINGS, T1),
        lambda: t.update_settings(SETTINGS, T1),
        lambda: t.include_manually(TEMPLATE, SETTINGS, T1),
        lambda: t.record_operation_result(OP, True, T1),
    ]
    for command in commands:
        with pytest.raises(InvalidTableTransition):
            command()


def test_pause_resume_only_from_active_paused():
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
    t = excluded()
    assert t.needs_reconcile_workflow is False
    assert t.settings is None
    assert t.selection == TableSelection.MANUAL
    assert t.status == TableStatus.EXCLUDED


def test_exclude_sets_manual():
    t = auto()
    t.exclude(T1)
    assert (t.status, t.selection) == (TableStatus.EXCLUDED, TableSelection.MANUAL)


def test_needs_reconcile_workflow():
    t = auto()
    assert t.needs_reconcile_workflow
    t.pause(T1)
    assert t.needs_reconcile_workflow


def test_reset_to_auto_then_apply_include_decision():
    t = excluded()
    t.reset_to_auto(T1)
    assert t.selection == TableSelection.AUTO
    t.apply_auto_decision(RULE, TEMPLATE, SETTINGS, T1)
    assert t.status == TableStatus.ACTIVE
    assert t.settings == SETTINGS
    assert t.selection == TableSelection.AUTO
    assert t.matched_rule_id == RULE and t.source_template_id == TEMPLATE


def test_apply_include_keeps_existing_settings():
    t = auto()
    own = MaintenanceSettings(reconcile_interval=timedelta(hours=2))
    t.update_settings(own, T1)
    t.apply_auto_decision(RULE, TEMPLATE, SETTINGS, T1)
    assert t.settings == own


def test_apply_auto_decision_without_rule_excludes_auto_table():
    t = auto()
    t.apply_auto_decision(None, None, None, T1)
    assert t.status == TableStatus.EXCLUDED
    assert t.settings == SETTINGS
    assert t.selection == TableSelection.AUTO


def test_apply_exclude_rule_excludes_auto_table():
    t = auto()
    t.apply_auto_decision(DiscoveryRuleId("r2"), None, None, T1)
    assert t.status == TableStatus.EXCLUDED
    assert t.matched_rule_id == DiscoveryRuleId("r2")


def test_apply_auto_decision_ignored_for_manual():
    t = manual()
    t.apply_auto_decision(None, None, None, T1)
    assert t.status == TableStatus.ACTIVE
    assert t.updated_at == T0


def test_update_settings_requires_settings_capable_status():
    t = excluded()
    with pytest.raises(InvalidTableTransition):
        t.update_settings(SETTINGS, T1)
    a = auto()
    new = MaintenanceSettings(reconcile_interval=timedelta(hours=3))
    a.update_settings(new, T1)
    assert a.settings == new and a.updated_at == T1


def test_include_manually_reactivates_excluded_table():
    t = excluded()
    t.include_manually(TEMPLATE, SETTINGS, T1)
    assert (t.status, t.selection) == (TableStatus.ACTIVE, TableSelection.MANUAL)
    assert t.settings == SETTINGS
    assert t.source_template_id == TEMPLATE
    assert t.matched_rule_id is None


def test_include_manually_from_paused_auto_table():
    t = auto()
    t.pause(T1)
    t.include_manually(TEMPLATE, SETTINGS, T1)
    assert t.status == TableStatus.ACTIVE
    assert t.selection == TableSelection.MANUAL
    assert t.matched_rule_id is None


def test_backoff_doubles_and_caps():
    base = timedelta(hours=1)
    for failures, expected in [(0, 1), (1, 2), (3, 8), (10, 24)]:
        s = OperationState(consecutive_failures=failures)
        assert s.effective_cooldown(base) == timedelta(hours=expected)
    assert OperationState(consecutive_failures=2).effective_cooldown(
        timedelta(hours=30)
    ) == timedelta(hours=30)
    failed = OperationState().after_failure(T0).after_failure(T1)
    assert failed.consecutive_failures == 2 and failed.last_attempt_at == T1
    ok = failed.after_success(T1)
    assert ok.consecutive_failures == 0 and ok.last_attempt_at == T1


def test_record_operation_result():
    t = auto()
    assert t.operation_state(OP) == OperationState()
    t.record_operation_result(OP, False, T1)
    assert t.operation_state(OP).consecutive_failures == 1
    t.pause(T1)
    t.record_operation_result(OP, True, T1)
    assert t.operation_state(OP).consecutive_failures == 0
    assert t.updated_at == T1


def test_rename_keeps_identity():
    t = auto()
    new = TableName(catalog="iceberg", namespace="inventory", table="orders_v2")
    t.rename(new, T1)
    assert t.id == TableUuid("u1") and t.name == new
    assert t == auto()
