"""Define the policy_with_operation helper."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        ExpireSnapshotsSpec,
        MaintenancePolicyContent,
        RemoveOrphanFilesSpec,
        RewriteDataFilesSpec,
        RewriteManifestsSpec,
    )


def policy_with_operation(
    content: MaintenancePolicyContent,
    operation: MaintenanceOperation,
    spec: RewriteDataFilesSpec | RewriteManifestsSpec | ExpireSnapshotsSpec | RemoveOrphanFilesSpec | None,
) -> MaintenancePolicyContent:
    """Return ``content`` with the block of one operation replaced by ``spec``; None removes the block."""
    return content.with_changes(**{operation.value: spec})
