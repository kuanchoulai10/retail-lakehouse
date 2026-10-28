from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine

from adapter.outbound.discovery_rule.sql.discovery_rules_sql_repo import (
    DiscoveryRulesSqlRepo,
)
from application.domain.model.discovery_rule.discovery_rule import DiscoveryRule
from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.model.discovery_rule.table_pattern import TablePattern
from application.exceptions import ConflictError
from application.domain.model.table_maintenance_preset.table_maintenance_preset_id import (
    TableMaintenancePresetId,
)

NOW = datetime(2026, 10, 24, tzinfo=UTC)


def _include(rule_id: str, priority: int, preset: str = "t1") -> DiscoveryRule:
    return DiscoveryRule.create(
        DiscoveryRuleId(rule_id),
        priority,
        RuleEffect.INCLUDE,
        TablePattern("iceberg", "inv*", "*"),
        TableMaintenancePresetId(preset),
        True,
        NOW,
    )


@pytest.fixture
def repo(engine: Engine) -> DiscoveryRulesSqlRepo:
    return DiscoveryRulesSqlRepo(engine)


def test_roundtrip(repo: DiscoveryRulesSqlRepo):
    repo.create(_include("r1", 5))
    loaded = repo.get(DiscoveryRuleId("r1"))
    assert loaded is not None
    assert loaded.priority == 5
    assert loaded.effect is RuleEffect.INCLUDE
    assert loaded.pattern == TablePattern("iceberg", "inv*", "*")
    assert loaded.preset_id == TableMaintenancePresetId("t1")
    assert loaded.enabled is True
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at == NOW
    assert loaded.collect_events() == []


def test_exclude_rule_roundtrip_without_preset(repo: DiscoveryRulesSqlRepo):
    rule = DiscoveryRule.create(
        DiscoveryRuleId("x"),
        1,
        RuleEffect.EXCLUDE,
        TablePattern(),
        None,
        False,
        NOW,
    )
    repo.create(rule)
    loaded = repo.get(rule.id)
    assert loaded is not None
    assert loaded.preset_id is None
    assert loaded.enabled is False


def test_get_missing_returns_none(repo: DiscoveryRulesSqlRepo):
    assert repo.get(DiscoveryRuleId("nope")) is None


def test_update_persists(repo: DiscoveryRulesSqlRepo):
    rule = _include("r1", 5)
    repo.create(rule)
    later = datetime(2026, 11, 1, tzinfo=UTC)
    rule.update(9, RuleEffect.EXCLUDE, TablePattern("c", "n", "t"), None, False, later)
    repo.update(rule)
    loaded = repo.get(rule.id)
    assert loaded is not None
    assert loaded.priority == 9
    assert loaded.effect is RuleEffect.EXCLUDE
    assert loaded.pattern == TablePattern("c", "n", "t")
    assert loaded.preset_id is None
    assert loaded.enabled is False
    assert loaded.updated_at == later


def test_update_missing_raises(repo: DiscoveryRulesSqlRepo):
    with pytest.raises(LookupError):
        repo.update(_include("ghost", 1))


def test_delete(repo: DiscoveryRulesSqlRepo):
    repo.create(_include("r1", 1))
    repo.delete(DiscoveryRuleId("r1"))
    assert repo.get(DiscoveryRuleId("r1")) is None
    repo.delete(DiscoveryRuleId("r1"))


def test_list_all_ordered_by_priority_then_id(repo: DiscoveryRulesSqlRepo):
    repo.create(_include("b", 2))
    repo.create(_include("c", 1))
    repo.create(_include("a", 2))
    assert [r.id.value for r in repo.list_all()] == ["c", "a", "b"]


def test_count_by_preset(repo: DiscoveryRulesSqlRepo):
    repo.create(_include("r1", 1, "t1"))
    repo.create(_include("r2", 2, "t1"))
    repo.create(_include("r3", 3, "t2"))
    assert repo.count_by_preset(TableMaintenancePresetId("t1")) == 2
    assert repo.count_by_preset(TableMaintenancePresetId("t2")) == 1
    assert repo.count_by_preset(TableMaintenancePresetId("t3")) == 0


def test_create_duplicate_primary_key_raises_conflict(repo: DiscoveryRulesSqlRepo):
    repo.create(_include("r1", 1))
    with pytest.raises(ConflictError):
        repo.create(_include("r1", 2))
