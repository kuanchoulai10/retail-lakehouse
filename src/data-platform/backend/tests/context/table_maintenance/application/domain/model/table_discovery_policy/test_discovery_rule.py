"""Test DiscoveryRule: an action on the tables whose name matches a pattern."""

from __future__ import annotations

import pytest

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryRule,
    RuleAction,
    TableNamePattern,
)


def _rule(action: RuleAction, pattern: str) -> DiscoveryRule:
    return DiscoveryRule(action=action, table_name_pattern=TableNamePattern(value=pattern))


def test_the_actions_are_include_and_exclude() -> None:
    """The actions are include and exclude."""
    assert [action.value for action in RuleAction] == ["include", "exclude"]


@pytest.mark.parametrize(
    ("action", "pattern", "table", "expected"),
    [
        (RuleAction.INCLUDE, "*", "orders", True),
        (RuleAction.EXCLUDE, "*_tmp", "refunds_tmp", True),
        (RuleAction.EXCLUDE, "*_tmp", "orders", False),
    ],
)
def test_matches_when_the_pattern_matches_whatever_the_action(
    action: RuleAction, pattern: str, table: str, expected: bool
) -> None:
    """Matches when the pattern matches whatever the action."""
    assert _rule(action, pattern).matches(table) is expected
