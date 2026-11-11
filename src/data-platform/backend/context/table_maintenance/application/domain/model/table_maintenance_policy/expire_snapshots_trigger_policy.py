"""Define the ExpireSnapshotsTriggerPolicy alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_conditions import (
    ExpireSnapshotsConditions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.trigger_policy import TriggerPolicy

ExpireSnapshotsTriggerPolicy = TriggerPolicy[ExpireSnapshotsConditions]
