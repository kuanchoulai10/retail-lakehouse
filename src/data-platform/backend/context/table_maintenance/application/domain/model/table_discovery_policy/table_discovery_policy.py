"""Define the TableDiscoveryPolicy aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import PositiveInt

from base import AggregateRoot
from context.table_maintenance.application.domain.model.table_discovery_policy.default_discovery_policy_id import (
    DEFAULT_DISCOVERY_POLICY_ID,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.default_discovery_policy_is_fixed import (  # noqa: E501
    DefaultDiscoveryPolicyIsFixed,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.default_discovery_policy_name import (
    DEFAULT_DISCOVERY_POLICY_NAME,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_decision import (
    DiscoveryDecision,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_match import (
    DiscoveryMatch,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.discovery_policy_content import (
    DiscoveryPolicyContent,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.stale_discovery_policy_version import (
    StaleDiscoveryPolicyVersion,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_policy_id import (
    TableDiscoveryPolicyId,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_policy_name import (
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_policy_version import (
    TableDiscoveryPolicyVersion,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.unknown_discovery_rule_id import (
    UnknownDiscoveryRuleId,
)

if TYPE_CHECKING:
    from collections.abc import Collection

    from context.table_maintenance.application.domain.model.table import TableName
    from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_rule_id import (
        TableDiscoveryRuleId,
    )


class TableDiscoveryPolicy(AggregateRoot[TableDiscoveryPolicyId]):
    """A versioned discovery policy: which tables under its attachments are managed; each replacement is a new version.

    It is identified by its ``dp-`` id; its unique ``name`` is for display and URLs. Rule ids are the
    platform's: content may name only the ids its current version holds and those issued for the request.
    The platform default (``DEFAULT_DISCOVERY_POLICY_ID``) is fixed at version 1 and never replaced.
    """

    id: TableDiscoveryPolicyId
    name: TableDiscoveryPolicyName
    content: DiscoveryPolicyContent
    version: PositiveInt
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        name: TableDiscoveryPolicyName,
        content: DiscoveryPolicyContent,
        now: datetime,
        *,
        new_rule_ids: Collection[TableDiscoveryRuleId] = (),
    ) -> TableDiscoveryPolicy:
        """Create a policy at version 1, under a new ``dp-`` id; every rule id must be one of ``new_rule_ids``."""
        _refuse_unknown_rule_ids(content, new_rule_ids)
        return cls(
            id=TableDiscoveryPolicyId.new(), name=name, content=content, version=1, created_at=now, updated_at=now
        )

    @classmethod
    def create_default(cls, now: datetime) -> TableDiscoveryPolicy:
        """Create the platform default at version 1: the fixed id, the name ``default`` and the platform content."""
        return cls(
            id=DEFAULT_DISCOVERY_POLICY_ID,
            name=TableDiscoveryPolicyName(value=DEFAULT_DISCOVERY_POLICY_NAME),
            content=DiscoveryPolicyContent.platform_default(),
            version=1,
            created_at=now,
            updated_at=now,
        )

    def replace(
        self,
        content: DiscoveryPolicyContent,
        expected_version: int,
        now: datetime,
        *,
        new_rule_ids: Collection[TableDiscoveryRuleId] = (),
    ) -> None:
        """Replace the content as the next version.

        Refused, in this order and leaving the policy unchanged: a change to the default
        (``DefaultDiscoveryPolicyIsFixed``), a stale ``expected_version`` (``StaleDiscoveryPolicyVersion``),
        and a rule id that is neither in the current version nor one of ``new_rule_ids``
        (``UnknownDiscoveryRuleId``), so a client can keep a rule's id but never choose one.
        """
        if self.is_default:
            raise DefaultDiscoveryPolicyIsFixed("the default discovery policy cannot be changed")
        if expected_version != self.version:
            raise StaleDiscoveryPolicyVersion(
                f"discovery policy {self.name.value} is at version {self.version}, not {expected_version}"
            )
        _refuse_unknown_rule_ids(content, self.content.rule_ids() | frozenset(new_rule_ids))
        self._assign_together(content=content, version=self.version + 1, updated_at=now)

    def current_version(self) -> TableDiscoveryPolicyVersion:
        """Return the current content as a version record."""
        return TableDiscoveryPolicyVersion(
            policy_id=self.id, version=self.version, content=self.content, created_at=self.updated_at
        )

    @property
    def is_default(self) -> bool:
        """Return whether this is the platform default, told by its fixed id."""
        return self.id == DEFAULT_DISCOVERY_POLICY_ID

    def decide(self, name: TableName) -> DiscoveryDecision:
        """Decide the table by the first matching rule, or by ``no_match_outcome`` with no rule."""
        rule = self.content.deciding_rule(name)
        outcome = self.content.no_match_outcome if rule is None else rule.outcome
        return DiscoveryDecision(
            outcome=outcome,
            match=DiscoveryMatch(
                policy_id=self.id, policy_version=self.version, rule_id=None if rule is None else rule.id
            ),
        )

    def can_manage(self) -> bool:
        """Return whether some table could resolve to ``manage`` under this policy."""
        return self.content.can_manage()


def _refuse_unknown_rule_ids(content: DiscoveryPolicyContent, allowed: Collection[TableDiscoveryRuleId]) -> None:
    unknown = [rule.id for rule in content.rules if rule.id not in allowed]
    if unknown:
        raise UnknownDiscoveryRuleId(f"unknown discovery rule id {unknown[0].value}")
