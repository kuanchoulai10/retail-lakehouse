"""Test DiscoveryRules: the last matching rule decides."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryRule,
    DiscoveryRules,
    RuleAction,
    TableNamePattern,
)


def _rules(*specs: tuple[RuleAction, str]) -> DiscoveryRules:
    return DiscoveryRules(
        rules=tuple(
            DiscoveryRule(action=action, table_name_pattern=TableNamePattern(value=pattern))
            for action, pattern in specs
        )
    )


INCLUDE = RuleAction.INCLUDE
EXCLUDE = RuleAction.EXCLUDE


@pytest.mark.parametrize(
    ("specs", "table", "expected"),
    [
        ([(INCLUDE, "*")], "orders", (True, 1)),
        ([(INCLUDE, "*"), (EXCLUDE, "*_tmp")], "refunds_tmp", (False, 2)),
        ([(INCLUDE, "*"), (EXCLUDE, "*_tmp")], "orders", (True, 1)),
        ([(INCLUDE, "*"), (EXCLUDE, "*_tmp"), (INCLUDE, "orders_tmp")], "orders_tmp", (True, 3)),
        ([(INCLUDE, "orders"), (INCLUDE, "customers")], "budget", (False, None)),
        ([(EXCLUDE, "*")], "x", (False, 1)),
    ],
)
def test_manages_by_the_last_matching_rule(
    specs: list[tuple[RuleAction, str]], table: str, expected: tuple[bool, int | None]
) -> None:
    """Manages by the last matching rule."""
    assert _rules(*specs).manages(table) == expected


def test_deciding_position_is_one_based_and_the_last_match() -> None:
    """Deciding position is one based and the last match."""
    rules = _rules((INCLUDE, "*"), (EXCLUDE, "*_tmp"), (INCLUDE, "orders_tmp"))

    assert rules.deciding_position("orders_tmp") == 3
    assert rules.deciding_position("refunds_tmp") == 2
    assert rules.deciding_position("orders") == 1


def test_deciding_position_is_none_when_nothing_matches() -> None:
    """Deciding position is none when nothing matches."""
    assert _rules((INCLUDE, "orders")).deciding_position("budget") is None


def test_no_rules_is_refused() -> None:
    """No rules is refused."""
    with pytest.raises(InvariantViolation, match="at least one rule"):
        DiscoveryRules(rules=())
