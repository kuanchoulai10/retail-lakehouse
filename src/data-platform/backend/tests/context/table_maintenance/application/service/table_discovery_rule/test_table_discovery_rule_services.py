"""Test the discovery rule use case services."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.exceptions import (
    NotFoundError,
    ValidationError,
)
from context.table_maintenance.application.port.inbound.table_discovery_rule import (
    CreateTableDiscoveryRuleUseCaseInput,
    DeleteTableDiscoveryRuleUseCaseInput,
    ListTableDiscoveryRulesUseCaseInput,
    UpdateTableDiscoveryRuleUseCaseInput,
)
from context.table_maintenance.application.service.table_discovery_rule import (
    CreateTableDiscoveryRuleService,
    DeleteTableDiscoveryRuleService,
    ListTableDiscoveryRulesService,
    UpdateTableDiscoveryRuleService,
)


def _rule(rules_repo, now, rid="r-1", priority=10):
    rule = TableDiscoveryRule.create(
        TableDiscoveryRuleId(rid),
        priority,
        RuleEffect.INCLUDE,
        TablePattern(),
        True,
        now,
    )
    rules_repo.create(rule)
    return rule


def test_create_include_rule(rules_repo, clock, new_id):
    """Creating an include rule stores it with its patterns and a generated id."""
    service = CreateTableDiscoveryRuleService(rules_repo, clock=clock, new_id=new_id)
    out = service.execute(
        CreateTableDiscoveryRuleUseCaseInput(
            priority=5,
            effect="include",
            namespace_pattern="sales*",
        )
    )
    assert out.id == "id-1"
    assert out.catalog_pattern == "*"
    assert out.namespace_pattern == "sales*"
    assert out.table_pattern == "*"
    assert out.enabled is True
    assert rules_repo.get(TableDiscoveryRuleId("id-1")) is not None


def test_create_exclude_rule(rules_repo, clock, new_id):
    """Creating an exclude rule stores it with its pattern."""
    service = CreateTableDiscoveryRuleService(rules_repo, clock=clock, new_id=new_id)
    out = service.execute(CreateTableDiscoveryRuleUseCaseInput(priority=1, effect="exclude", table_pattern="tmp_*"))
    assert out.effect == "exclude"


def test_create_rule_unknown_effect_is_rejected(rules_repo, clock, new_id):
    """An unknown effect is rejected and nothing is stored."""
    service = CreateTableDiscoveryRuleService(rules_repo, clock=clock, new_id=new_id)
    with pytest.raises(ValidationError):
        service.execute(CreateTableDiscoveryRuleUseCaseInput(priority=1, effect="bogus"))
    assert rules_repo.list_all() == []


def test_update_rule_replaces_definition(rules_repo, clock, now):
    """Updating a rule replaces its priority, effect, flag and patterns."""
    _rule(rules_repo, now)
    out = UpdateTableDiscoveryRuleService(rules_repo, clock=clock).execute(
        UpdateTableDiscoveryRuleUseCaseInput(id="r-1", priority=2, effect="exclude", table_pattern="x*", enabled=False)
    )
    assert (out.priority, out.effect, out.enabled) == (2, "exclude", False)
    assert out.table_pattern == "x*"
    assert out.catalog_pattern == "*"


def test_update_unknown_rule_not_found(rules_repo, clock):
    """Updating an unknown rule raises NotFoundError."""
    with pytest.raises(NotFoundError):
        UpdateTableDiscoveryRuleService(rules_repo, clock=clock).execute(
            UpdateTableDiscoveryRuleUseCaseInput(id="nope", priority=1, effect="exclude")
        )


def test_update_rule_unknown_effect_leaves_rule_unchanged(rules_repo, clock, now):
    """An invalid update is rejected and leaves the stored rule unchanged."""
    _rule(rules_repo, now)
    with pytest.raises(ValidationError):
        UpdateTableDiscoveryRuleService(rules_repo, clock=clock).execute(
            UpdateTableDiscoveryRuleUseCaseInput(id="r-1", priority=99, effect="bogus")
        )
    stored = rules_repo.get(TableDiscoveryRuleId("r-1"))
    assert stored is not None
    assert stored.priority == 10


def test_delete_rule(rules_repo, now):
    """Deleting a rule removes it."""
    _rule(rules_repo, now)
    DeleteTableDiscoveryRuleService(rules_repo).execute(DeleteTableDiscoveryRuleUseCaseInput(id="r-1"))
    assert rules_repo.list_all() == []


def test_delete_unknown_rule_not_found(rules_repo):
    """Deleting an unknown rule raises NotFoundError."""
    with pytest.raises(NotFoundError):
        DeleteTableDiscoveryRuleService(rules_repo).execute(DeleteTableDiscoveryRuleUseCaseInput(id="nope"))


def test_list_rules_ordered_by_priority(rules_repo, now):
    """Listing returns the rules ordered by priority."""
    _rule(rules_repo, now, rid="r-2", priority=20)
    _rule(rules_repo, now, rid="r-1", priority=10)
    out = ListTableDiscoveryRulesService(rules_repo).execute(ListTableDiscoveryRulesUseCaseInput())
    assert [i.id for i in out.items] == ["r-1", "r-2"]
