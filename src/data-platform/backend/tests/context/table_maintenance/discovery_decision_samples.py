"""Sample management decisions for tests that register a table without running a scan.

``MANAGED`` and ``UNMANAGED`` are what a policy at version 1 decided: managed by its first rule,
or unmanaged because none of its rules matched. ``UNMANAGED.decided_by`` is what to pass to
``Table.unmanage``.
"""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import TableDiscoveryPolicyId
from context.table_maintenance.application.domain.model.table_discovery_policy import DecidedBy, ManagementDecision

SAMPLE_POLICY_ID = TableDiscoveryPolicyId("dp-00000000000000000000000001")
SAMPLE_RULE_POSITION = 1
MANAGED = ManagementDecision(
    manage=True,
    decided_by=DecidedBy(policy_id=SAMPLE_POLICY_ID, policy_version=1, rule_position=SAMPLE_RULE_POSITION),
)
UNMANAGED = ManagementDecision(
    manage=False,
    decided_by=DecidedBy(policy_id=SAMPLE_POLICY_ID, policy_version=1, rule_position=None),
)
