"""Define the discovery_rules_of function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryRule,
    DiscoveryRules,
    RuleAction,
    TableNamePattern,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

_FIELDS = ("action", "table_name_pattern")


def discovery_rules_of(rules: Sequence[Mapping[str, str]]) -> DiscoveryRules:
    """Return the domain rules of a port input's rules, in the order sent.

    Each rule holds exactly ``action`` and ``table_name_pattern``. A missing or an unknown field raises a
    ValueError naming it and the rule's position (never a KeyError, which would read as not found); an
    unknown action, an empty pattern or no rule at all raises the domain's InvariantViolation.
    """
    built: list[DiscoveryRule] = []
    for position, rule in enumerate(rules, start=1):
        missing = [field for field in _FIELDS if field not in rule]
        unknown = sorted(set(rule) - set(_FIELDS))
        if missing or unknown:
            problems = [f"missing field {f}" for f in missing] + [f"unknown field {f}" for f in unknown]
            raise ValueError(f"rule {position}: {', '.join(problems)}")
        built.append(
            DiscoveryRule(
                action=RuleAction(rule["action"]),
                table_name_pattern=TableNamePattern(value=rule["table_name_pattern"]),
            )
        )
    return DiscoveryRules(rules=tuple(built))
