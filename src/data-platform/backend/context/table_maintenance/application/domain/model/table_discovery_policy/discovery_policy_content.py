"""Define the DiscoveryPolicyContent value object."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Self

from pydantic import model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_outcome import (
    DiscoveryOutcome,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_rule import (
    TableDiscoveryRule,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName
    from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_rule_id import (
        TableDiscoveryRuleId,
    )

_PLATFORM_DEFAULT_DESCRIPTION = (
    "Manages nothing. Attach another discovery policy to a catalog, namespace or table to manage its tables."
)


class DiscoveryPolicyContent(ValueObject):
    """Hold what a discovery policy says: ordered rules and the outcome when none of them matches.

    The rules are read top to bottom, and the first whose conditions all hold decides; the list order
    is the only order. When no rule matches, ``no_match_outcome`` decides. Rule ids are unique.
    """

    description: str = ""
    rules: tuple[TableDiscoveryRule, ...] = ()
    no_match_outcome: DiscoveryOutcome

    @model_validator(mode="after")
    def _rule_ids_are_unique(self) -> Self:
        for rule_id, count in Counter(rule.id for rule in self.rules).items():
            if count > 1:
                raise ValueError(f"discovery rule {rule_id.value} appears more than once")
        return self

    @classmethod
    def platform_default(cls) -> Self:
        """Return the content of the platform default: no rules, and every table unmanaged."""
        return cls(description=_PLATFORM_DEFAULT_DESCRIPTION, rules=(), no_match_outcome=DiscoveryOutcome.UNMANAGE)

    def deciding_rule(self, name: TableName) -> TableDiscoveryRule | None:
        """Return the first rule that matches the table, or None when none does."""
        return next((rule for rule in self.rules if rule.matches(name)), None)

    def can_manage(self) -> bool:
        """Return whether some table could resolve to ``manage``: a rule manages, or the no-match outcome does.

        The check is syntactic: a ``manage`` rule that an earlier catch-all ``unmanage`` hides still counts,
        so it errs towards scanning.
        """
        return self.no_match_outcome is DiscoveryOutcome.MANAGE or any(
            rule.outcome is DiscoveryOutcome.MANAGE for rule in self.rules
        )

    def rule_ids(self) -> frozenset[TableDiscoveryRuleId]:
        """Return the ids of the rules."""
        return frozenset(rule.id for rule in self.rules)
