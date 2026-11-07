"""Test the discovery rule use case services."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
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


@pytest.fixture
def preset(presets_repo, now):
    """Provide a stored preset for the rules to point to."""
    t = TableMaintenancePreset.create(TableMaintenancePresetId("t-1"), "gold", MaintenanceSettings(), now)
    presets_repo.create(t)
    return t


def _rule(rules_repo, now, rid="r-1", priority=10):
    rule = TableDiscoveryRule.create(
        TableDiscoveryRuleId(rid),
        priority,
        RuleEffect.INCLUDE,
        TablePattern(),
        TableMaintenancePresetId("t-1"),
        True,
        now,
    )
    rules_repo.create(rule)
    return rule


def test_create_include_rule(rules_repo, presets_repo, preset, clock, new_id):
    """Creating an include rule stores it with its patterns and a generated id."""
    service = CreateTableDiscoveryRuleService(rules_repo, presets_repo, clock=clock, new_id=new_id)
    out = service.execute(
        CreateTableDiscoveryRuleUseCaseInput(
            priority=5,
            effect="include",
            namespace_pattern="sales*",
            preset_id="t-1",
        )
    )
    assert out.id == "id-1"
    assert out.catalog_pattern == "*"
    assert out.namespace_pattern == "sales*"
    assert out.table_pattern == "*"
    assert out.preset_id == "t-1"
    assert out.enabled is True
    assert rules_repo.get(TableDiscoveryRuleId("id-1")) is not None


def test_create_exclude_rule_without_preset(rules_repo, presets_repo, clock, new_id):
    """Creating an exclude rule needs no preset."""
    service = CreateTableDiscoveryRuleService(rules_repo, presets_repo, clock=clock, new_id=new_id)
    out = service.execute(CreateTableDiscoveryRuleUseCaseInput(priority=1, effect="exclude", table_pattern="tmp_*"))
    assert out.effect == "exclude"
    assert out.preset_id is None


def test_create_rule_unknown_preset_not_found(rules_repo, presets_repo, clock, new_id):
    """Creating a rule with an unknown preset raises NotFoundError."""
    service = CreateTableDiscoveryRuleService(rules_repo, presets_repo, clock=clock, new_id=new_id)
    with pytest.raises(NotFoundError):
        service.execute(CreateTableDiscoveryRuleUseCaseInput(priority=1, effect="include", preset_id="missing"))


@pytest.mark.parametrize(
    "effect, preset_id",
    [("include", None), ("bogus", "t-1"), ("exclude", "t-1")],
)
def test_create_rule_invalid_combination(rules_repo, presets_repo, preset, clock, new_id, effect, preset_id):
    """An invalid effect and preset combination is rejected and nothing is stored."""
    service = CreateTableDiscoveryRuleService(rules_repo, presets_repo, clock=clock, new_id=new_id)
    with pytest.raises(ValidationError):
        service.execute(CreateTableDiscoveryRuleUseCaseInput(priority=1, effect=effect, preset_id=preset_id))
    assert rules_repo.list_all() == []


def test_update_rule_replaces_definition(rules_repo, presets_repo, preset, clock, now):
    """Updating a rule replaces its priority, effect, preset, flag and patterns."""
    _rule(rules_repo, now)
    out = UpdateTableDiscoveryRuleService(rules_repo, presets_repo, clock=clock).execute(
        UpdateTableDiscoveryRuleUseCaseInput(id="r-1", priority=2, effect="exclude", table_pattern="x*", enabled=False)
    )
    assert (out.priority, out.effect, out.preset_id, out.enabled) == (
        2,
        "exclude",
        None,
        False,
    )
    assert out.table_pattern == "x*"
    assert out.catalog_pattern == "*"


def test_update_unknown_rule_not_found(rules_repo, presets_repo, clock):
    """Updating an unknown rule raises NotFoundError."""
    with pytest.raises(NotFoundError):
        UpdateTableDiscoveryRuleService(rules_repo, presets_repo, clock=clock).execute(
            UpdateTableDiscoveryRuleUseCaseInput(id="nope", priority=1, effect="exclude")
        )


def test_update_rule_unknown_preset_not_found(rules_repo, presets_repo, preset, clock, now):
    """Updating a rule to an unknown preset raises NotFoundError."""
    _rule(rules_repo, now)
    with pytest.raises(NotFoundError):
        UpdateTableDiscoveryRuleService(rules_repo, presets_repo, clock=clock).execute(
            UpdateTableDiscoveryRuleUseCaseInput(id="r-1", priority=1, effect="include", preset_id="missing")
        )


def test_update_rule_invalid_leaves_rule_unchanged(rules_repo, presets_repo, preset, clock, now):
    """An invalid update is rejected and leaves the stored rule unchanged."""
    _rule(rules_repo, now)
    with pytest.raises(ValidationError):
        UpdateTableDiscoveryRuleService(rules_repo, presets_repo, clock=clock).execute(
            UpdateTableDiscoveryRuleUseCaseInput(id="r-1", priority=99, effect="include")
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
