"""Define the applied_policy_ref_of function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import AppliedPolicyRef
from context.table_maintenance.application.domain.model.table_maintenance_policy import TableMaintenancePolicyId

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
        ResolveApplicableTableMaintenancePolicyUseCaseOutput,
    )


def applied_policy_ref_of(applied: ResolveApplicableTableMaintenancePolicyUseCaseOutput) -> AppliedPolicyRef:
    """Return the reference to the policy a resolution found to apply, by its id."""
    return AppliedPolicyRef(
        policy_id=TableMaintenancePolicyId(applied.policy_id), version=applied.version, target=applied.target
    )
