"""Sample discovery decisions for tests that register a table without running a scan.

``MANAGED`` and ``UNMANAGED`` are what a policy at version 1 decided: managed by its rule
``dr-…01``, or unmanaged by its no-match outcome. ``UNMANAGED.match`` is the match to pass to
``Table.unmanage``.
"""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_discovery_policy import (
    DiscoveryDecision,
    DiscoveryMatch,
    DiscoveryOutcome,
    TableDiscoveryPolicyId,
    TableDiscoveryRuleId,
)

SAMPLE_POLICY_ID = TableDiscoveryPolicyId("dp-00000000000000000000000001")
SAMPLE_RULE_ID = TableDiscoveryRuleId("dr-00000000000000000000000001")
MANAGED = DiscoveryDecision(
    outcome=DiscoveryOutcome.MANAGE,
    match=DiscoveryMatch(policy_id=SAMPLE_POLICY_ID, policy_version=1, rule_id=SAMPLE_RULE_ID),
)
UNMANAGED = DiscoveryDecision(
    outcome=DiscoveryOutcome.UNMANAGE,
    match=DiscoveryMatch(policy_id=SAMPLE_POLICY_ID, policy_version=1, rule_id=None),
)
