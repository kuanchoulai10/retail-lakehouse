"""Define the ExpireSnapshotsSpec alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_options import (
    ExpireSnapshotsOptions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.expire_snapshots_target import (
    ExpireSnapshotsTarget,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.operation_spec import (
    OperationSpec,
)

ExpireSnapshotsSpec = OperationSpec[ExpireSnapshotsTarget, ExpireSnapshotsOptions]
"""The ``expire_snapshots`` block of a policy."""
