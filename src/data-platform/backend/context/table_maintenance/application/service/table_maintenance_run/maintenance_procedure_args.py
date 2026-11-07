"""Define the maintenance_procedure_args function."""

from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING, Any

from context.table_maintenance.application.domain.model.shared import (
    MaintenanceOperation,
)
from context.table_maintenance.application.domain.service.shared import (
    resolve_target_file_size,
)

if TYPE_CHECKING:
    from datetime import datetime

    from context.table_maintenance.application.domain.model.shared import (
        MaintenanceSettings,
    )

MIN_INPUT_FILES = 2


def maintenance_procedure_args(
    operation: MaintenanceOperation,
    settings: MaintenanceSettings,
    properties: dict[str, str],
    now: datetime,
) -> dict[str, Any]:
    """Return the primitive Iceberg procedure arguments of one operation.

    ``now`` must be timezone-aware. ``older_than`` is ``now`` minus the configured
    age, rendered as ISO-8601 with a ``+00:00`` offset. Option keys use the Iceberg
    spelling.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    match operation:
        case MaintenanceOperation.REWRITE_DATA_FILES:
            return {
                "target-file-size-bytes": resolve_target_file_size(settings.rewrite_data_files, properties),
                "min-input-files": MIN_INPUT_FILES,
                "partial-progress.enabled": True,
            }
        case MaintenanceOperation.REWRITE_MANIFESTS:
            return {}
        case MaintenanceOperation.EXPIRE_SNAPSHOTS:
            cfg = settings.expire_snapshots
            return {
                "older_than": (now - cfg.older_than).astimezone(UTC).isoformat(),
                "retain_last": cfg.retain_last,
            }
        case MaintenanceOperation.REMOVE_ORPHAN_FILES:
            return {"older_than": ((now - settings.remove_orphan_files.older_than).astimezone(UTC).isoformat())}
