"""Define the OperationPolicies value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_policy import (
    ExpireSnapshotsPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_policy import (
    RemoveOrphanFilesPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_policy import (
    RewriteDataFilesPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_policy import (
    RewriteManifestsPolicy,
)


class OperationPolicies(ValueObject):
    """Bundle the policy of each maintenance operation."""

    rewrite_data_files: RewriteDataFilesPolicy
    rewrite_manifests: RewriteManifestsPolicy
    expire_snapshots: ExpireSnapshotsPolicy
    remove_orphan_files: RemoveOrphanFilesPolicy

    def for_operation(
        self, operation: MaintenanceOperation
    ) -> RewriteDataFilesPolicy | RewriteManifestsPolicy | ExpireSnapshotsPolicy | RemoveOrphanFilesPolicy:
        """Return the policy of one operation."""
        match operation:
            case MaintenanceOperation.REWRITE_DATA_FILES:
                return self.rewrite_data_files
            case MaintenanceOperation.REWRITE_MANIFESTS:
                return self.rewrite_manifests
            case MaintenanceOperation.EXPIRE_SNAPSHOTS:
                return self.expire_snapshots
            case MaintenanceOperation.REMOVE_ORPHAN_FILES:
                return self.remove_orphan_files
