from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from application.domain.model.discovery_rule import (
    DiscoveryRule,
    DiscoveryRuleId,
    InvalidDiscoveryRule,
    RuleEffect,
    TablePattern,
)
from application.domain.model.policy_template import PolicyTemplateId

T0 = datetime(2026, 1, 1, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)


def make(
    effect=RuleEffect.INCLUDE, template_id=PolicyTemplateId("t1")
) -> DiscoveryRule:
    return DiscoveryRule.create(
        id=DiscoveryRuleId("r1"),
        priority=10,
        effect=effect,
        pattern=TablePattern(),
        template_id=template_id,
        enabled=True,
        now=T0,
    )


def test_create():
    r = make()
    assert r.priority == 10
    assert r.enabled
    assert r.created_at == r.updated_at == T0


def test_include_rule_requires_template():
    with pytest.raises(InvalidDiscoveryRule):
        make(RuleEffect.INCLUDE, None)


def test_exclude_rule_rejects_template():
    with pytest.raises(InvalidDiscoveryRule):
        make(RuleEffect.EXCLUDE, PolicyTemplateId("t1"))
    assert make(RuleEffect.EXCLUDE, None).template_id is None


def test_update():
    r = make()
    r.update(
        priority=5,
        effect=RuleEffect.EXCLUDE,
        pattern=TablePattern(table="tmp_*"),
        template_id=None,
        enabled=False,
        now=T1,
    )
    assert r.priority == 5
    assert r.effect == RuleEffect.EXCLUDE
    assert r.template_id is None
    assert not r.enabled
    assert r.updated_at == T1
    assert r.created_at == T0


def test_invalid_update_leaves_state_unchanged():
    r = make()
    with pytest.raises(InvalidDiscoveryRule):
        r.update(
            priority=5,
            effect=RuleEffect.INCLUDE,
            pattern=TablePattern(),
            template_id=None,
            enabled=False,
            now=T1,
        )
    assert r.priority == 10
    assert r.enabled
    assert r.updated_at == T0
