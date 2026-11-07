"""Test the TableDiscoveryRule aggregate: creation, effect and preset rules, and updates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    InvalidTableDiscoveryRule,
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
DEFAULT_PRESET_ID = TableMaintenancePresetId("t1")


def make(effect=RuleEffect.INCLUDE, preset_id=DEFAULT_PRESET_ID) -> TableDiscoveryRule:
    """Build a discovery rule with the given effect and preset."""
    return TableDiscoveryRule.create(
        id=TableDiscoveryRuleId("r1"),
        priority=10,
        effect=effect,
        pattern=TablePattern(),
        preset_id=preset_id,
        enabled=True,
        now=T0,
    )


def test_create():
    """A new rule is enabled and stamped with its creation time."""
    r = make()
    assert r.priority == 10
    assert r.enabled
    assert r.created_at == r.updated_at == T0


def test_include_rule_requires_preset():
    """An include rule without a preset is rejected."""
    with pytest.raises(InvalidTableDiscoveryRule):
        make(RuleEffect.INCLUDE, None)


def test_exclude_rule_rejects_preset():
    """An exclude rule that names a preset is rejected."""
    with pytest.raises(InvalidTableDiscoveryRule):
        make(RuleEffect.EXCLUDE, TableMaintenancePresetId("t1"))
    assert make(RuleEffect.EXCLUDE, None).preset_id is None


def test_update():
    """An update changes the priority, effect and preset."""
    r = make()
    r.update(
        priority=5,
        effect=RuleEffect.EXCLUDE,
        pattern=TablePattern(table="tmp_*"),
        preset_id=None,
        enabled=False,
        now=T1,
    )
    assert r.priority == 5
    assert r.effect == RuleEffect.EXCLUDE
    assert r.preset_id is None
    assert not r.enabled
    assert r.updated_at == T1
    assert r.created_at == T0


def test_invalid_update_leaves_state_unchanged():
    """An invalid update is rejected and leaves the rule as it was."""
    r = make()
    with pytest.raises(InvalidTableDiscoveryRule):
        r.update(
            priority=5,
            effect=RuleEffect.INCLUDE,
            pattern=TablePattern(),
            preset_id=None,
            enabled=False,
            now=T1,
        )
    assert r.priority == 10
    assert r.enabled
    assert r.updated_at == T0
