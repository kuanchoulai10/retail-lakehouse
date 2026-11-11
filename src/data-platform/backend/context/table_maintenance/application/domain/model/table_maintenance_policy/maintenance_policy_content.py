"""Define the MaintenancePolicyContent value object."""

from __future__ import annotations

from datetime import timedelta
from typing import Self

from pydantic import Field

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import PositiveDuration
from context.table_maintenance.application.domain.model.table_maintenance_policy.at_least import AtLeast
from context.table_maintenance.application.domain.model.table_maintenance_policy.compaction_scope import CompactionScope
from context.table_maintenance.application.domain.model.table_maintenance_policy.compaction_unit import CompactionUnit
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_conditions import (
    ExpireSnapshotsConditions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_execution_policy import (  # noqa: E501
    ExpireSnapshotsExecutionPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_policy import (
    ExpireSnapshotsPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_trigger_policy import (  # noqa: E501
    ExpireSnapshotsTriggerPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.operation_policies import (
    OperationPolicies,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.partial_progress import PartialProgress
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_conditions import (
    RemoveOrphanFilesConditions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_execution_policy import (  # noqa: E501
    RemoveOrphanFilesExecutionPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_policy import (
    RemoveOrphanFilesPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_trigger_policy import (  # noqa: E501
    RemoveOrphanFilesTriggerPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_conditions import (
    RewriteDataFilesConditions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_execution_policy import (  # noqa: E501
    RewriteDataFilesExecutionPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_policy import (
    RewriteDataFilesPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_trigger_policy import (  # noqa: E501
    RewriteDataFilesTriggerPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_conditions import (
    RewriteManifestsConditions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_execution_policy import (  # noqa: E501
    RewriteManifestsExecutionPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_policy import (
    RewriteManifestsPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_trigger_policy import (  # noqa: E501
    RewriteManifestsTriggerPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.small_manifests_condition import (
    SmallManifestsCondition,
)


class MaintenancePolicyContent(ValueObject):
    """Hold what a maintenance policy says: reconcile interval, dry run and each operation's policy."""

    description: str
    reconcile_interval: PositiveDuration = Field(
        validation_alias="reconcile_interval_seconds",
        serialization_alias="reconcile_interval_seconds",
    )
    dry_run: bool
    operations: OperationPolicies

    @classmethod
    def platform_default(cls) -> Self:
        """Return the content of the policy every table falls back to."""
        return cls(
            description="Platform default",
            reconcile_interval=timedelta(hours=1),
            dry_run=False,
            operations=OperationPolicies(
                rewrite_data_files=RewriteDataFilesPolicy(
                    enabled=True,
                    scope=CompactionScope(unit=CompactionUnit.PARTITION),
                    trigger_policy=RewriteDataFilesTriggerPolicy(
                        cooldown=timedelta(hours=1),
                        conditions=RewriteDataFilesConditions(reducible_files=AtLeast(at_least=5)),
                    ),
                    execution_policy=RewriteDataFilesExecutionPolicy(
                        min_input_files=2,
                        partial_progress=PartialProgress(enabled=True),
                    ),
                ),
                rewrite_manifests=RewriteManifestsPolicy(
                    enabled=True,
                    trigger_policy=RewriteManifestsTriggerPolicy(
                        cooldown=timedelta(hours=6),
                        conditions=RewriteManifestsConditions(
                            small_manifests=SmallManifestsCondition(at_least=5),
                        ),
                    ),
                    execution_policy=RewriteManifestsExecutionPolicy(),
                ),
                expire_snapshots=ExpireSnapshotsPolicy(
                    enabled=True,
                    trigger_policy=ExpireSnapshotsTriggerPolicy(
                        cooldown=timedelta(hours=6),
                        conditions=ExpireSnapshotsConditions(expirable_snapshots=AtLeast(at_least=1)),
                    ),
                    execution_policy=ExpireSnapshotsExecutionPolicy(
                        older_than=timedelta(days=1),
                        retain_last=10,
                    ),
                ),
                remove_orphan_files=RemoveOrphanFilesPolicy(
                    enabled=True,
                    trigger_policy=RemoveOrphanFilesTriggerPolicy(
                        cooldown=timedelta(days=7),
                        conditions=RemoveOrphanFilesConditions(),
                    ),
                    execution_policy=RemoveOrphanFilesExecutionPolicy(older_than=timedelta(days=3)),
                ),
            ),
        )
