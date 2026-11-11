"""Test the SQL repository of the TableDiscoveryRules aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from context.table_maintenance.adapter.outbound.table_discovery_rules.sql import (
    TableDiscoveryRulesSqlRepo,
)
from context.table_maintenance.application.port.outbound.table_discovery_rules import (
    GLOBAL_TABLE_DISCOVERY_RULES_ID,
    GlobList,
    RuleAction,
    StaleDiscoveryRulesVersion,
    TableDiscoveryRule,
    TableDiscoveryRuleId,
    TableDiscoveryRules,
)

if TYPE_CHECKING:
    from sqlalchemy import Engine

NOW = datetime(2026, 11, 1, tzinfo=UTC)


def _rule(rid: str, priority: int, action: RuleAction = RuleAction.INCLUDE, *, enabled: bool = True):
    return TableDiscoveryRule.create(
        id=TableDiscoveryRuleId(rid),
        priority=priority,
        action=action,
        enabled=enabled,
        catalogs=GlobList(globs=("iceberg", "lake")),
        namespaces=GlobList(globs=("prod.*",)),
        tables=GlobList(globs=("tmp_*", "staging_*")),
        now=NOW,
    )


def _replaced(repo: TableDiscoveryRulesSqlRepo, *rules: TableDiscoveryRule, at: datetime = NOW) -> TableDiscoveryRules:
    aggregate = repo.get_rules()
    aggregate.replace(rules, aggregate.version, at, new_ids={rule.id for rule in rules})
    return aggregate


@pytest.fixture
def repo(engine: Engine) -> TableDiscoveryRulesSqlRepo:
    """Provide the discovery rules repository on the test engine."""
    return TableDiscoveryRulesSqlRepo(engine)


def test_nothing_saved_reads_as_empty_version_zero(repo: TableDiscoveryRulesSqlRepo):
    """Before the first save the rules are empty at version 0."""
    rules = repo.get_rules()
    assert (rules.id, rules.rules, rules.version) == (GLOBAL_TABLE_DISCOVERY_RULES_ID, (), 0)


def test_save_round_trips_every_field_in_priority_order(repo: TableDiscoveryRulesSqlRepo):
    """A saved list loads back whole, in priority order, with its globs and timestamps."""
    repo.save(_replaced(repo, _rule("b", 20, RuleAction.EXCLUDE, enabled=False), _rule("a", 10)))
    loaded = repo.get_rules()
    assert loaded.version == 1
    assert [(r.id.value, r.priority, r.action, r.enabled) for r in loaded.rules] == [
        ("a", 10, RuleAction.INCLUDE, True),
        ("b", 20, RuleAction.EXCLUDE, False),
    ]
    first = loaded.rules[0]
    assert (first.catalogs, first.namespaces, first.tables) == (
        GlobList(globs=("iceberg", "lake")),
        GlobList(globs=("prod.*",)),
        GlobList(globs=("tmp_*", "staging_*")),
    )
    assert first.created_at == NOW
    assert first.created_at.tzinfo is not None
    assert repo.get(GLOBAL_TABLE_DISCOVERY_RULES_ID) == loaded
    assert repo.list_all() == [loaded]


def test_save_replaces_every_rule(repo: TableDiscoveryRulesSqlRepo):
    """A second save adds, edits and deletes rules at once."""
    repo.save(_replaced(repo, _rule("a", 10), _rule("b", 20)))
    repo.save(_replaced(repo, _rule("b", 5), _rule("c", 30), at=NOW + timedelta(hours=1)))
    loaded = repo.get_rules()
    assert (loaded.version, [(r.id.value, r.priority) for r in loaded.rules]) == (2, [("b", 5), ("c", 30)])


def test_concurrent_save_from_the_same_version_is_stale(repo: TableDiscoveryRulesSqlRepo):
    """Of two saves replaced from one version, the second is stale and changes nothing."""
    first = _replaced(repo, _rule("a", 10))
    second = _replaced(repo, _rule("z", 99))
    repo.save(first)
    with pytest.raises(StaleDiscoveryRulesVersion):
        repo.save(second)
    assert [r.id.value for r in repo.get_rules().rules] == ["a"]


def test_concurrent_later_save_is_stale(repo: TableDiscoveryRulesSqlRepo):
    """A save from an older stored version is stale once the list moved on."""
    repo.save(_replaced(repo, _rule("a", 10)))
    first = _replaced(repo, _rule("b", 10))
    second = _replaced(repo, _rule("c", 10))
    repo.save(first)
    with pytest.raises(StaleDiscoveryRulesVersion):
        repo.save(second)
    assert [r.id.value for r in repo.get_rules().rules] == ["b"]
