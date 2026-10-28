"""Define the MaintenanceSettings value object."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from application.domain.model.shared.maintenance_operation import (
    MaintenanceOperation,
)
from application.domain.model.shared.expire_snapshots_settings import (
    ExpireSnapshotsSettings,
)
from application.domain.model.shared.invalid_maintenance_settings import (
    InvalidMaintenanceSettings,
)
from application.domain.model.shared.remove_orphan_files_settings import (
    RemoveOrphanFilesSettings,
)
from application.domain.model.shared.rewrite_data_files_settings import (
    RewriteDataFilesSettings,
)
from application.domain.model.shared.rewrite_manifests_settings import (
    RewriteManifestsSettings,
)
from base.value_object import ValueObject

type OperationSettings = (
    RewriteDataFilesSettings
    | RewriteManifestsSettings
    | ExpireSnapshotsSettings
    | RemoveOrphanFilesSettings
)


@dataclass(frozen=True)
class MaintenanceSettings(ValueObject):
    """Bundle the reconcile interval and per-operation settings of a table."""

    reconcile_interval: timedelta = field(default_factory=lambda: timedelta(hours=1))
    rewrite_data_files: RewriteDataFilesSettings = field(
        default_factory=RewriteDataFilesSettings
    )
    rewrite_manifests: RewriteManifestsSettings = field(
        default_factory=RewriteManifestsSettings
    )
    expire_snapshots: ExpireSnapshotsSettings = field(
        default_factory=ExpireSnapshotsSettings
    )
    remove_orphan_files: RemoveOrphanFilesSettings = field(
        default_factory=RemoveOrphanFilesSettings
    )

    def __post_init__(self) -> None:
        """Reject a non-positive reconcile interval."""
        if self.reconcile_interval <= timedelta(0):
            raise InvalidMaintenanceSettings("reconcile_interval must be positive")

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
