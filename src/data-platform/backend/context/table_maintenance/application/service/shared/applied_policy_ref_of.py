"""Define the applied_policy_ref_of function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table import AppliedPolicyRef

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
        ResolveApplicableTableMaintenancePolicyUseCaseOutput,
    )


def applied_policy_ref_of(applied: ResolveApplicableTableMaintenancePolicyUseCaseOutput) -> AppliedPolicyRef:
    """Return the reference to the policy a resolution found to apply."""
    return AppliedPolicyRef(name=applied.policy_name, version=applied.version, target=applied.target)
