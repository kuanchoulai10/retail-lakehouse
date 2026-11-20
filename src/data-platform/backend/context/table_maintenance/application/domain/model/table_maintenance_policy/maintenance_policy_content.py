"""Define the MaintenancePolicyContent value object."""

from __future__ import annotations

from datetime import timedelta
from typing import Self

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy.at_most import AtMost
from context.table_maintenance.application.domain.model.table_maintenance_policy.catalog_commit_trigger import (
    CatalogCommitTrigger,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.compaction_unit import CompactionUnit
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_spec import (
    ExpireSnapshotsSpec,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_target import (
    ExpireSnapshotsTarget,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.maintenance_triggers import (
    MaintenanceTriggers,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_spec import (
    RemoveOrphanFilesSpec,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_target import (
    RemoveOrphanFilesTarget,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_options import (
    RewriteDataFilesOptions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_spec import (
    RewriteDataFilesSpec,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_target import (
    RewriteDataFilesTarget,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_spec import (
    RewriteManifestsSpec,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_target import (
    RewriteManifestsTarget,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.schedule_trigger import (
    ScheduleTrigger,
)


class MaintenancePolicyContent(ValueObject):
    """Hold what a maintenance policy says: when a table is checked and the target state of each operation.

    An operation whose block is absent is not done; a policy may hold no block at all. Each block holds
    the target the table is kept at and the options its procedure runs with. Cooldowns are the platform's.
    """

    description: str
    on: MaintenanceTriggers
    dry_run: bool = False
    rewrite_data_files: RewriteDataFilesSpec | None = None
    rewrite_manifests: RewriteManifestsSpec | None = None
    expire_snapshots: ExpireSnapshotsSpec | None = None
    remove_orphan_files: RemoveOrphanFilesSpec | None = None

    @classmethod
    def platform_default(cls) -> Self:
        """Return the content of the policy every table falls back to."""
        return cls(
            description="Platform default",
            on=MaintenanceTriggers(
                schedule=ScheduleTrigger(every=timedelta(hours=1)),
                catalog_commit=CatalogCommitTrigger(debounce=timedelta(minutes=5)),
            ),
            dry_run=False,
            rewrite_data_files=RewriteDataFilesSpec(
                target=RewriteDataFilesTarget(reducible_files=AtMost(at_most=5), per=CompactionUnit.PARTITION),
                options=RewriteDataFilesOptions(min_input_files=2, partial_progress_enabled=True),
            ),
            rewrite_manifests=RewriteManifestsSpec(
                target=RewriteManifestsTarget(small_manifests=AtMost(at_most=5)),
            ),
            expire_snapshots=ExpireSnapshotsSpec(
                target=ExpireSnapshotsTarget(min_snapshots_to_keep=10, max_snapshot_age=timedelta(days=1)),
            ),
            remove_orphan_files=RemoveOrphanFilesSpec(
                target=RemoveOrphanFilesTarget(older_than=timedelta(days=3)),
            ),
        )

    def spec_for(
        self, operation: MaintenanceOperation
    ) -> RewriteDataFilesSpec | RewriteManifestsSpec | ExpireSnapshotsSpec | RemoveOrphanFilesSpec | None:
        """Return the block of ``operation``, or None when the policy leaves it out."""
        match operation:
            case MaintenanceOperation.REWRITE_DATA_FILES:
                return self.rewrite_data_files
            case MaintenanceOperation.REWRITE_MANIFESTS:
                return self.rewrite_manifests
            case MaintenanceOperation.EXPIRE_SNAPSHOTS:
                return self.expire_snapshots
            case MaintenanceOperation.REMOVE_ORPHAN_FILES:
                return self.remove_orphan_files
