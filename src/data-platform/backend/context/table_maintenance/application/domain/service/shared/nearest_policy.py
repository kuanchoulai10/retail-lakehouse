"""Define the NearestPolicy value object."""

from __future__ import annotations

from base import EntityId, ValueObject
from context.table_maintenance.application.domain.model.shared import PolicyTarget


class NearestPolicy[ID: EntityId](ValueObject):
    """The policy of one kind nearest to a place, and where it is attached.

    ``target`` is the table, namespace or catalog holding it; ``policy_id`` is the policy's id, a
    ``TableDiscoveryPolicyId`` or a ``TableMaintenancePolicyId`` as the kind walked.
    """

    target: PolicyTarget
    policy_id: ID
