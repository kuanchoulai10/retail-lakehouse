"""Test applied_policy_ref_of: the reference to the policy a resolution found to apply."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.shared import (
    PolicyTarget,
    PolicyTargetType,
    TableMaintenancePolicyId,
)
from context.table_maintenance.application.domain.model.table import AppliedPolicyRef
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
    ResolveApplicableTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.service.shared import applied_policy_ref_of

NIGHTLY = "mp-00000000000000000000000001"


def _applied(target: dict | None) -> ResolveApplicableTableMaintenancePolicyUseCaseOutput:
    return ResolveApplicableTableMaintenancePolicyUseCaseOutput(
        policy_id=NIGHTLY, policy_name="nightly", version=4, content={}, target=target
    )


def test_refers_to_an_attached_policy_by_id_version_and_typed_target():
    """An attached policy is referred to by its id, version and the target it is attached to, typed."""
    ref = applied_policy_ref_of(_applied({"type": "namespace", "path": ["iceberg", "e2e"]}))
    assert ref == AppliedPolicyRef(
        policy_id=TableMaintenancePolicyId(NIGHTLY),
        version=4,
        target=PolicyTarget(type=PolicyTargetType.NAMESPACE, path=("iceberg", "e2e")),
    )


def test_refers_to_the_platform_default_without_a_target():
    """The platform default, attached to nothing, is referred to without a target."""
    ref = applied_policy_ref_of(_applied(None))
    assert ref == AppliedPolicyRef(policy_id=TableMaintenancePolicyId(NIGHTLY), version=4)
