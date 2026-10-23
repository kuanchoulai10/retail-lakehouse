"""Define the DiscoveryRule aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from application.domain.model.discovery_rule.discovery_rule_id import DiscoveryRuleId
from application.domain.model.discovery_rule.invalid_discovery_rule import (
    InvalidDiscoveryRule,
)
from application.domain.model.discovery_rule.rule_effect import RuleEffect
from application.domain.model.discovery_rule.table_pattern import TablePattern
from application.domain.model.policy_template.policy_template_id import (
    PolicyTemplateId,
)
from base.aggregate_root import AggregateRoot


def _validate(effect: RuleEffect, template_id: PolicyTemplateId | None) -> None:
    if effect == RuleEffect.INCLUDE and template_id is None:
        raise InvalidDiscoveryRule("an include rule requires a template")
    if effect == RuleEffect.EXCLUDE and template_id is not None:
        raise InvalidDiscoveryRule("an exclude rule must not have a template")


@dataclass(eq=False)
class DiscoveryRule(AggregateRoot[DiscoveryRuleId]):
    """Decide whether discovered tables matching a pattern are managed."""

    id: DiscoveryRuleId
    priority: int
    effect: RuleEffect
    pattern: TablePattern
    template_id: PolicyTemplateId | None
    enabled: bool
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """Enforce the effect and template invariant."""
        _validate(self.effect, self.template_id)

    @classmethod
    def create(
        cls,
        id: DiscoveryRuleId,  # noqa: A002
        priority: int,
        effect: RuleEffect,
        pattern: TablePattern,
        template_id: PolicyTemplateId | None,
        enabled: bool,
        now: datetime,
    ) -> DiscoveryRule:
        """Create a rule."""
        return cls(
            id=id,
            priority=priority,
            effect=effect,
            pattern=pattern,
            template_id=template_id,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        priority: int,
        effect: RuleEffect,
        pattern: TablePattern,
        template_id: PolicyTemplateId | None,
        enabled: bool,
        now: datetime,
    ) -> None:
        """Replace the rule's definition, leaving it unchanged if invalid."""
        _validate(effect, template_id)
        self.priority = priority
        self.effect = effect
        self.pattern = pattern
        self.template_id = template_id
        self.enabled = enabled
        self.updated_at = now
