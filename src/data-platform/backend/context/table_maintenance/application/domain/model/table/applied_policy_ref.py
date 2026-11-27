"""Define the AppliedPolicyRef value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import PolicyTarget, TableMaintenancePolicyId


class AppliedPolicyRef(ValueObject):
    """Point at the maintenance policy that applied to a table: its id, version and the target it is attached to.

    ``target`` is None for the platform default policy, which is attached to nothing.
    """

    policy_id: TableMaintenancePolicyId
    version: int
    target: PolicyTarget | None = None

    def names_the_same_application_as(self, other: AppliedPolicyRef) -> bool:
        """Return whether ``other`` is the same policy version attached at the same target.

        Targets compare by their key, so a table target is its uuid: the table's own policy read
        under a renamed or moved table's new path is the same application.
        """
        return (
            self.policy_id == other.policy_id
            and self.version == other.version
            and _key(self.target) == _key(other.target)
        )


def _key(target: PolicyTarget | None) -> str | None:
    return None if target is None else target.key()
