"""Define the TableDiscoveryRules aggregate root."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Self

from pydantic import NonNegativeInt, model_validator

from base import AggregateRoot
from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DEFAULT_DISCOVERY_POLICY_ID,
    TableDiscoveryPolicyId,
    UnknownDiscoveryRuleId,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.stale_discovery_rules_version import (
    StaleDiscoveryRulesVersion,
)
from context.table_maintenance.application.domain.model.table_discovery_rules.table_discovery_rule import (
    TableDiscoveryRule,
)

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table import TableName
    from context.table_maintenance.application.domain.model.table_discovery_policy import TableDiscoveryRuleId


class TableDiscoveryRules(AggregateRoot[TableDiscoveryPolicyId]):
    """The ordered discovery rules of the platform, versioned and replaced as a whole.

    Priorities are unique, so the first enabled rule that matches a table, in
    priority order, decides it. The list is the consistency boundary: it is only
    ever replaced whole, from the version it was read at.
    """

    id: TableDiscoveryPolicyId
    rules: tuple[TableDiscoveryRule, ...]
    version: NonNegativeInt

    @model_validator(mode="after")
    def _unique_and_ordered(self) -> Self:
        for rule_id, count in Counter(rule.id for rule in self.rules).items():
            if count > 1:
                raise ValueError(f"discovery rule {rule_id.value} appears more than once")
        for priority, count in Counter(rule.priority for rule in self.rules).items():
            if count > 1:
                raise ValueError(f"priority {priority} is used by more than one discovery rule")
        priorities = [rule.priority for rule in self.rules]
        if priorities != sorted(priorities):
            raise ValueError("discovery rules must be in priority order")
        return self

    @classmethod
    def empty(cls) -> TableDiscoveryRules:
        """Return the platform's rules before any were saved: none, at version 0."""
        return cls(id=DEFAULT_DISCOVERY_POLICY_ID, rules=(), version=0)

    def replace(
        self,
        rules: Sequence[TableDiscoveryRule],
        expected_version: int,
        now: datetime,
        *,
        new_ids: Collection[TableDiscoveryRuleId] = (),
    ) -> None:
        """Replace every rule as the next version; reject a stale expected_version.

        Every rule is either one already in the list, by id, or one of new_ids;
        any other id is rejected, so a client cannot mint ids. A rule kept by id
        keeps its creation time, and its update time too when its definition did
        not change; a new rule is created at now. An invalid list leaves the
        rules unchanged.
        """
        if expected_version != self.version:
            raise StaleDiscoveryRulesVersion(f"discovery rules are at version {self.version}, not {expected_version}")
        current = {rule.id: rule for rule in self.rules}
        unknown = [rule.id for rule in rules if rule.id not in current and rule.id not in new_ids]
        if unknown:
            raise UnknownDiscoveryRuleId(f"unknown discovery rule id {unknown[0].value}")
        merged = [_revise(current.get(rule.id), rule, now) for rule in rules]
        self._assign_together(
            rules=tuple(sorted(merged, key=lambda rule: rule.priority)),
            version=self.version + 1,
        )

    def decide(self, name: TableName) -> TableDiscoveryRule | None:
        """Return the first enabled rule, in priority order, that matches the table, or None."""
        return next((rule for rule in self.rules if rule.enabled and rule.matches(name)), None)


def _revise(previous: TableDiscoveryRule | None, rule: TableDiscoveryRule, now: datetime) -> TableDiscoveryRule:
    if previous is not None and previous.same_definition(rule):
        return previous
    return TableDiscoveryRule(
        id=rule.id,
        priority=rule.priority,
        action=rule.action,
        enabled=rule.enabled,
        catalogs=rule.catalogs,
        namespaces=rule.namespaces,
        tables=rule.tables,
        created_at=now if previous is None else previous.created_at,
        updated_at=now,
    )
