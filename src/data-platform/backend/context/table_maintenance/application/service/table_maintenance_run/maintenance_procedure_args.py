"""Define the maintenance_procedure_args function."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.service.shared import (
    resolve_execution_target_file_size,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table_maintenance_policy import (
        MaintenancePolicyContent,
    )


def maintenance_procedure_args(
    operation: MaintenanceOperation,
    policy: MaintenancePolicyContent,
    properties: dict[str, str],
    now: datetime,
) -> dict[str, Any]:
    """Return the primitive Iceberg procedure arguments of one operation, from its execution policy.

    ``now`` must be timezone-aware. ``older_than`` is ``now`` minus the configured
    age, rendered as ISO-8601 with a ``+00:00`` offset. Option keys use the Iceberg
    spelling.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    operations = policy.operations
    match operation:
        case MaintenanceOperation.REWRITE_DATA_FILES:
            execution = operations.rewrite_data_files.execution_policy
            args: dict[str, Any] = {
                "target-file-size-bytes": resolve_execution_target_file_size(execution, properties),
                "min-input-files": execution.min_input_files,
                "partial-progress.enabled": execution.partial_progress.enabled,
            }
            if execution.partial_progress.max_commits is not None:
                args["partial-progress.max-commits"] = execution.partial_progress.max_commits
            return args
        case MaintenanceOperation.REWRITE_MANIFESTS:
            return {}
        case MaintenanceOperation.EXPIRE_SNAPSHOTS:
            snapshots = operations.expire_snapshots.execution_policy
            return {
                "older_than": (now - snapshots.older_than).astimezone(UTC).isoformat(),
                "retain_last": snapshots.retain_last,
            }
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            orphans = operations.remove_orphan_files.execution_policy
            return {"older_than": (now - orphans.older_than).astimezone(UTC).isoformat()}
