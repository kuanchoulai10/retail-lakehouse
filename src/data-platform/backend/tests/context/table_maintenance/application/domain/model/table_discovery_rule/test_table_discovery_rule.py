"""Test the TableDiscoveryRule aggregate: creation and updates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def make(effect=RuleEffect.INCLUDE) -> TableDiscoveryRule:
    """Build a discovery rule with the given effect."""
    return TableDiscoveryRule.create(
        id=TableDiscoveryRuleId("r1"),
        priority=10,
        effect=effect,
        pattern=TablePattern(),
        enabled=True,
        now=T0,
    )


def test_create():
    """A new rule is enabled and stamped with its creation time."""
    r = make()
    assert r.priority == 10
    assert r.enabled
    assert r.created_at == r.updated_at == T0


def test_update():
    """An update changes the priority, effect, pattern and flag."""
    r = make()
    r.update(
        priority=5,
        effect=RuleEffect.EXCLUDE,
        pattern=TablePattern(table="tmp_*"),
        enabled=False,
        now=T1,
    )
    assert r.priority == 5
    assert r.effect == RuleEffect.EXCLUDE
    assert not r.enabled
    assert r.updated_at == T1
    assert r.created_at == T0


def test_rule_rejects_wrong_type_on_assignment():
    """Assigning a wrong type to a field is rejected."""
    r = make()
    with pytest.raises(ValidationError):
        r.priority = "high"  # ty: ignore[invalid-assignment]


def test_table_pattern_is_immutable():
    """A pattern cannot be changed after creation."""
    p = TablePattern()
    with pytest.raises(ValidationError):
        p.table = "x"


def test_update_with_wrong_type_leaves_rule_unchanged():
    """A wrong-typed argument is rejected before anything is assigned."""
    r = make()
    with pytest.raises(ValidationError):
        r.update(
            priority="high",  # ty: ignore[invalid-argument-type]
            effect=RuleEffect.INCLUDE,
            pattern=TablePattern(),
            enabled=False,
            now=T1,
        )
    assert r.priority == 10
    assert r.enabled
    assert r.updated_at == T0
