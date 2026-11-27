"""Define the TableDiscoveryPolicy aggregate root."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import PositiveInt

from base import AggregateRoot
from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table_discovery_policy.decision.decided_by import DecidedBy
from context.table_maintenance.application.domain.model.table_discovery_policy.decision.management_decision import (
    ManagementDecision,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.rule.discovery_rules import (
    DiscoveryRules,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.stale_discovery_policy_version import (
    StaleDiscoveryPolicyVersion,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_policy_name import (
    TableDiscoveryPolicyName,
)
from context.table_maintenance.application.domain.model.table_discovery_policy.table_discovery_policy_version import (
    TableDiscoveryPolicyVersion,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableName


class TableDiscoveryPolicy(AggregateRoot[TableDiscoveryPolicyId]):
    """A versioned discovery policy: which tables under where it is attached are managed.

    It is identified by its ``dp-`` id; its unique ``name`` is for display and URLs. Its ``rules`` are
    read top to bottom and the last one whose table name pattern matches decides: an include manages
    the table, an exclude does not, and a table no rule matches is not managed. Each revision of the
    description and rules is a new version.
    """

    id: TableDiscoveryPolicyId
    name: TableDiscoveryPolicyName
    description: str
    rules: DiscoveryRules
    version: PositiveInt
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        name: TableDiscoveryPolicyName,
        description: str,
        rules: DiscoveryRules,
        now: datetime,
    ) -> TableDiscoveryPolicy:
        """Create a policy at version 1, under a new ``dp-`` id."""
        return cls(
            id=TableDiscoveryPolicyId.new(),
            name=name,
            description=description,
            rules=rules,
            version=1,
            created_at=now,
            updated_at=now,
        )

    def revise(self, description: str, rules: DiscoveryRules, expected_version: int, now: datetime) -> None:
        """Replace the description and rules as the next version.

        A revision from a version that is not the current one raises ``StaleDiscoveryPolicyVersion``
        and leaves the policy unchanged.
        """
        if expected_version != self.version:
            raise StaleDiscoveryPolicyVersion(
                f"discovery policy {self.name.value} is at version {self.version}, not {expected_version}"
            )
        self._assign_together(description=description, rules=rules, version=self.version + 1, updated_at=now)

    def current_version(self) -> TableDiscoveryPolicyVersion:
        """Return the current description and rules as a version record."""
        return TableDiscoveryPolicyVersion(
            policy_id=self.id,
            version=self.version,
            description=self.description,
            rules=self.rules,
            created_at=self.updated_at,
        )

    def should_manage(self, table: TableName) -> ManagementDecision:
        """Decide the table by the last rule its table name matches, naming this version and that rule's position."""
        manage, position = self.rules.manages(table.table)
        return ManagementDecision(
            manage=manage,
            decided_by=DecidedBy(policy_id=self.id, policy_version=self.version, rule_position=position),
        )
