"""Outbound ports shared by the aggregates that hold policies: where each policy is attached."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    PolicyPlacement,
    PolicyTarget,
    PolicyTargetType,
    TableDiscoveryPolicyId,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.port.outbound.shared.policy_placements_store import PolicyPlacementsStore

__all__ = [
    "PolicyPlacement",
    "PolicyPlacementsStore",
    "PolicyTarget",
    "PolicyTargetType",
    "TableDiscoveryPolicyId",
    "TableMaintenancePolicyId",
]
