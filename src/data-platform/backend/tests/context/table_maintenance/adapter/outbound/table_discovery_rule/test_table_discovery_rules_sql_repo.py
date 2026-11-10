"""Test the SQL repository of the TableDiscoveryRule aggregate."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.table_discovery_rule.sql import (
    TableDiscoveryRulesSqlRepo,
)
from context.table_maintenance.application.domain.model.table_discovery_rule import (
    RuleEffect,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TablePattern,
)
from context.table_maintenance.application.domain.model.table_maintenance_preset import (
    TableMaintenancePresetId,
)
from context.table_maintenance.application.exceptions import ConflictError

if TYPE_CHECKING:
    from sqlalchemy import Engine

NOW = datetime(2026, 10, 24, tzinfo=UTC)


def _include(rule_id: str, priority: int, preset: str = "t1") -> TableDiscoveryRule:
    return TableDiscoveryRule.create(
        TableDiscoveryRuleId(rule_id),
        priority,
        RuleEffect.INCLUDE,
        TablePattern(catalog="iceberg", namespace="inv*", table="*"),
        TableMaintenancePresetId(preset),
        True,
        NOW,
    )


@pytest.fixture
def repo(engine: Engine) -> TableDiscoveryRulesSqlRepo:
    """Provide the discovery rules repository on the test engine."""
    return TableDiscoveryRulesSqlRepo(engine)


def test_roundtrip(repo: TableDiscoveryRulesSqlRepo):
    """A stored include rule loads back with its priority and effect."""
    repo.create(_include("r1", 5))
    loaded = repo.get(TableDiscoveryRuleId("r1"))
    assert loaded is not None
    assert loaded.priority == 5
    assert loaded.effect is RuleEffect.INCLUDE
    assert loaded.pattern == TablePattern(catalog="iceberg", namespace="inv*", table="*")
    assert loaded.preset_id == TableMaintenancePresetId("t1")
    assert loaded.enabled is True
    assert loaded.created_at == NOW
    assert loaded.created_at.tzinfo is not None
    assert loaded.updated_at == NOW
    assert loaded.collect_events() == []


def test_exclude_rule_roundtrip_without_preset(repo: TableDiscoveryRulesSqlRepo):
    """A disabled exclude rule without a preset round trips with no preset."""
    rule = TableDiscoveryRule.create(
        TableDiscoveryRuleId("x"),
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


def test_get_missing_returns_none(repo: TableDiscoveryRulesSqlRepo):
    """Getting a rule that does not exist returns None."""
    assert repo.get(TableDiscoveryRuleId("nope")) is None


def test_update_persists(repo: TableDiscoveryRulesSqlRepo):
    """An update persists the new priority and effect."""
    rule = _include("r1", 5)
    repo.create(rule)
    later = datetime(2026, 11, 1, tzinfo=UTC)
    rule.update(9, RuleEffect.EXCLUDE, TablePattern(catalog="c", namespace="n", table="t"), None, False, later)
    repo.update(rule)
    loaded = repo.get(rule.id)
    assert loaded is not None
    assert loaded.priority == 9
    assert loaded.effect is RuleEffect.EXCLUDE
    assert loaded.pattern == TablePattern(catalog="c", namespace="n", table="t")
    assert loaded.preset_id is None
    assert loaded.enabled is False
    assert loaded.updated_at == later


def test_update_missing_raises(repo: TableDiscoveryRulesSqlRepo):
    """Updating a rule that does not exist raises LookupError."""
    with pytest.raises(LookupError):
        repo.update(_include("ghost", 1))


def test_delete(repo: TableDiscoveryRulesSqlRepo):
    """A deleted rule can no longer be loaded."""
    repo.create(_include("r1", 1))
    repo.delete(TableDiscoveryRuleId("r1"))
    assert repo.get(TableDiscoveryRuleId("r1")) is None
    repo.delete(TableDiscoveryRuleId("r1"))


def test_list_all_ordered_by_priority_then_id(repo: TableDiscoveryRulesSqlRepo):
    """Listing orders rules by priority and then by id."""
    repo.create(_include("b", 2))
    repo.create(_include("c", 1))
    repo.create(_include("a", 2))
    assert [r.id.value for r in repo.list_all()] == ["c", "a", "b"]


def test_count_by_preset(repo: TableDiscoveryRulesSqlRepo):
    """Counting by preset returns how many rules point to each preset."""
    repo.create(_include("r1", 1, "t1"))
    repo.create(_include("r2", 2, "t1"))
    repo.create(_include("r3", 3, "t2"))
    assert repo.count_by_preset(TableMaintenancePresetId("t1")) == 2
    assert repo.count_by_preset(TableMaintenancePresetId("t2")) == 1
    assert repo.count_by_preset(TableMaintenancePresetId("t3")) == 0


def test_create_duplicate_primary_key_raises_conflict(repo: TableDiscoveryRulesSqlRepo):
    """Creating a rule with an existing id raises ConflictError."""
    repo.create(_include("r1", 1))
    with pytest.raises(ConflictError):
        repo.create(_include("r1", 2))


def test_roundtrip_reads_an_equal_aggregate(repo: TableDiscoveryRulesSqlRepo):
    """A stored row reads back with the same dump and the same field types."""
    original = _include("r1", 5)
    repo.create(original)
    loaded = repo.get(TableDiscoveryRuleId("r1"))
    assert loaded is not None
    assert loaded.model_dump() == original.model_dump()
    assert {k: type(v) for k, v in loaded.model_dump().items()} == {
        k: type(v) for k, v in original.model_dump().items()
    }
