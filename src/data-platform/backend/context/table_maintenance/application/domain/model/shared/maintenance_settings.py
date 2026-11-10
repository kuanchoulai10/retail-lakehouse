"""Define the MaintenanceSettings value object."""

from __future__ import annotations

from datetime import timedelta

from pydantic import Field

from base.model import ValueObject
from context.table_maintenance.application.domain.model.shared.expire_snapshots_settings import (
    ExpireSnapshotsSettings,
)
from context.table_maintenance.application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.model.shared.positive_duration import (
    PositiveDuration,
)
from context.table_maintenance.application.domain.model.shared.remove_orphan_files_settings import (
    RemoveOrphanFilesSettings,
)
from context.table_maintenance.application.domain.model.shared.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)
from context.table_maintenance.application.domain.model.shared.rewrite_manifests_settings import (
    RewriteManifestsSettings,
)

type OperationSettings = (
    RewriteDataFilesSettings | RewriteManifestsSettings | ExpireSnapshotsSettings | RemoveOrphanFilesSettings
)


class MaintenanceSettings(ValueObject):
    """Bundle the reconcile interval and per-operation settings of a table."""

    reconcile_interval: PositiveDuration = Field(
        default=timedelta(hours=1),
        validation_alias="reconcile_interval_seconds",
        serialization_alias="reconcile_interval_seconds",
    )
    dry_run: bool = False
    rewrite_data_files: RewriteDataFilesSettings = Field(default_factory=RewriteDataFilesSettings)
    rewrite_manifests: RewriteManifestsSettings = Field(default_factory=RewriteManifestsSettings)
    expire_snapshots: ExpireSnapshotsSettings = Field(default_factory=ExpireSnapshotsSettings)
    remove_orphan_files: RemoveOrphanFilesSettings = Field(default_factory=RemoveOrphanFilesSettings)

    def for_operation(self, operation: MaintenanceOperation) -> OperationSettings:
        """Return the settings of one operation."""
        match operation:
            case MaintenanceOperation.REWRITE_DATA_FILES:
                return self.rewrite_data_files
            case MaintenanceOperation.REWRITE_MANIFESTS:
                return self.rewrite_manifests
            case MaintenanceOperation.EXPIRE_SNAPSHOTS:
                return self.expire_snapshots
            case MaintenanceOperation.REMOVE_ORPHAN_FILES:
                return self.remove_orphan_files

    def min_interval(self, operation: MaintenanceOperation) -> timedelta:
        """Return the minimum interval between runs of an operation."""
        return self.for_operation(operation).min_interval

    def enabled(self, operation: MaintenanceOperation) -> bool:
        """Return whether an operation is enabled."""
        return self.for_operation(operation).enabled
