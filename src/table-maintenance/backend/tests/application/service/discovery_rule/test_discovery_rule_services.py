"""Test the discovery rule use case services."""

from __future__ import annotations

import pytest

from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.model.discovery_rule.table_pattern import TablePattern
from application.domain.model.maintenance_settings.maintenance_settings import (
    MaintenanceSettings,
)
from application.domain.model.policy_template.policy_template import PolicyTemplate
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from application.exceptions import NotFoundError, ValidationError
from application.port.inbound.discovery_rule.create_discovery_rule import (
    CreateDiscoveryRuleUseCaseInput,
)
from application.port.inbound.discovery_rule.delete_discovery_rule import (
    DeleteDiscoveryRuleUseCaseInput,
)
from application.port.inbound.discovery_rule.list_discovery_rules import (
    ListDiscoveryRulesUseCaseInput,
)
from application.port.inbound.discovery_rule.update_discovery_rule import (
    UpdateDiscoveryRuleUseCaseInput,
)
from application.service.discovery_rule.create_discovery_rule import (
    CreateDiscoveryRuleService,
)
from application.service.discovery_rule.delete_discovery_rule import (
    DeleteDiscoveryRuleService,
)
from application.service.discovery_rule.list_discovery_rules import (
    ListDiscoveryRulesService,
)
from application.service.discovery_rule.update_discovery_rule import (
    UpdateDiscoveryRuleService,
)


@pytest.fixture
def template(templates_repo, now):
    t = PolicyTemplate.create(
        PolicyTemplateId("t-1"), "gold", MaintenanceSettings(), now
    )
    templates_repo.create(t)
    return t


def _rule(rules_repo, now, rid="r-1", priority=10):
    rule = DiscoveryRule.create(
        DiscoveryRuleId(rid),
        priority,
        RuleEffect.INCLUDE,
        TablePattern(),
        PolicyTemplateId("t-1"),
        True,
        now,
    )
    rules_repo.create(rule)
    return rule


def test_create_include_rule(rules_repo, templates_repo, template, clock, new_id):
    service = CreateDiscoveryRuleService(
        rules_repo, templates_repo, clock=clock, new_id=new_id
    )
    out = service.execute(
        CreateDiscoveryRuleUseCaseInput(
            priority=5,
            effect="include",
            namespace_pattern="sales*",
            template_id="t-1",
        )
    )
    assert out.id == "id-1"
    assert out.catalog_pattern == "*"
    assert out.namespace_pattern == "sales*"
    assert out.table_pattern == "*"
    assert out.template_id == "t-1"
    assert out.enabled is True
    assert rules_repo.get(DiscoveryRuleId("id-1")) is not None


def test_create_exclude_rule_without_template(
    rules_repo, templates_repo, clock, new_id
):
    service = CreateDiscoveryRuleService(
        rules_repo, templates_repo, clock=clock, new_id=new_id
    )
    out = service.execute(
        CreateDiscoveryRuleUseCaseInput(
            priority=1, effect="exclude", table_pattern="tmp_*"
        )
    )
    assert out.effect == "exclude"
    assert out.template_id is None


def test_create_rule_unknown_template_not_found(
    rules_repo, templates_repo, clock, new_id
):
    service = CreateDiscoveryRuleService(
        rules_repo, templates_repo, clock=clock, new_id=new_id
    )
    with pytest.raises(NotFoundError):
        service.execute(
            CreateDiscoveryRuleUseCaseInput(
                priority=1, effect="include", template_id="missing"
            )
        )


@pytest.mark.parametrize(
    "effect, template_id",
    [("include", None), ("bogus", "t-1"), ("exclude", "t-1")],
)
def test_create_rule_invalid_combination(
    rules_repo, templates_repo, template, clock, new_id, effect, template_id
):
    service = CreateDiscoveryRuleService(
        rules_repo, templates_repo, clock=clock, new_id=new_id
    )
    with pytest.raises(ValidationError):
        service.execute(
            CreateDiscoveryRuleUseCaseInput(
                priority=1, effect=effect, template_id=template_id
            )
        )
    assert rules_repo.list_all() == []


def test_update_rule_replaces_definition(
    rules_repo, templates_repo, template, clock, now
):
    _rule(rules_repo, now)
    out = UpdateDiscoveryRuleService(rules_repo, templates_repo, clock=clock).execute(
        UpdateDiscoveryRuleUseCaseInput(
            id="r-1", priority=2, effect="exclude", table_pattern="x*", enabled=False
        )
    )
    assert (out.priority, out.effect, out.template_id, out.enabled) == (
        2,
        "exclude",
        None,
        False,
    )
    assert out.table_pattern == "x*"
    assert out.catalog_pattern == "*"


def test_update_unknown_rule_not_found(rules_repo, templates_repo, clock):
    with pytest.raises(NotFoundError):
        UpdateDiscoveryRuleService(rules_repo, templates_repo, clock=clock).execute(
            UpdateDiscoveryRuleUseCaseInput(id="nope", priority=1, effect="exclude")
        )


def test_update_rule_unknown_template_not_found(
    rules_repo, templates_repo, template, clock, now
):
    _rule(rules_repo, now)
    with pytest.raises(NotFoundError):
        UpdateDiscoveryRuleService(rules_repo, templates_repo, clock=clock).execute(
            UpdateDiscoveryRuleUseCaseInput(
                id="r-1", priority=1, effect="include", template_id="missing"
            )
        )


def test_update_rule_invalid_leaves_rule_unchanged(
    rules_repo, templates_repo, template, clock, now
):
    _rule(rules_repo, now)
    with pytest.raises(ValidationError):
        UpdateDiscoveryRuleService(rules_repo, templates_repo, clock=clock).execute(
            UpdateDiscoveryRuleUseCaseInput(id="r-1", priority=99, effect="include")
        )
    stored = rules_repo.get(DiscoveryRuleId("r-1"))
    assert stored is not None
    assert stored.priority == 10


def test_delete_rule(rules_repo, now):
    _rule(rules_repo, now)
    DeleteDiscoveryRuleService(rules_repo).execute(
        DeleteDiscoveryRuleUseCaseInput(id="r-1")
    )
    assert rules_repo.list_all() == []


def test_delete_unknown_rule_not_found(rules_repo):
    with pytest.raises(NotFoundError):
        DeleteDiscoveryRuleService(rules_repo).execute(
            DeleteDiscoveryRuleUseCaseInput(id="nope")
        )


def test_list_rules_ordered_by_priority(rules_repo, now):
    _rule(rules_repo, now, rid="r-2", priority=20)
    _rule(rules_repo, now, rid="r-1", priority=10)
    out = ListDiscoveryRulesService(rules_repo).execute(
        ListDiscoveryRulesUseCaseInput()
    )
    assert [i.id for i in out.items] == ["r-1", "r-2"]
