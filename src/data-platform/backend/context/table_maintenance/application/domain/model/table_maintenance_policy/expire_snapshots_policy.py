"""Define the ExpireSnapshotsPolicy alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_execution_policy import (  # noqa: E501
    ExpireSnapshotsExecutionPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_trigger_policy import (  # noqa: E501
    ExpireSnapshotsTriggerPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.operation_policy import OperationPolicy

ExpireSnapshotsPolicy = OperationPolicy[ExpireSnapshotsTriggerPolicy, ExpireSnapshotsExecutionPolicy]
