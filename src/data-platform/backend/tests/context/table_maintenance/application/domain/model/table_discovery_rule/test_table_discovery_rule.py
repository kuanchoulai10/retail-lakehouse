from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    InvalidTableDiscoveryRule,
    RuleEffect,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def make(
    effect=RuleEffect.INCLUDE, preset_id=TableMaintenancePresetId("t1")
) -> TableDiscoveryRule:
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
    r = make()
    assert r.priority == 10
    assert r.enabled
    assert r.created_at == r.updated_at == T0


def test_include_rule_requires_preset():
    with pytest.raises(InvalidTableDiscoveryRule):
        make(RuleEffect.INCLUDE, None)


def test_exclude_rule_rejects_preset():
    with pytest.raises(InvalidTableDiscoveryRule):
        make(RuleEffect.EXCLUDE, TableMaintenancePresetId("t1"))
    assert make(RuleEffect.EXCLUDE, None).preset_id is None


def test_update():
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
