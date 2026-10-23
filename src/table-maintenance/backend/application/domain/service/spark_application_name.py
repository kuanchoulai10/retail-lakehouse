"""Define the spark_application_name domain service."""

from __future__ import annotations

from application.domain.model.maintenance.maintenance_operation import (
    MaintenanceOperation,
)

_CODES: dict[MaintenanceOperation, str] = {
    MaintenanceOperation.REWRITE_DATA_FILES: "rdf",
    MaintenanceOperation.REWRITE_MANIFESTS: "rm",
    MaintenanceOperation.EXPIRE_SNAPSHOTS: "es",
    MaintenanceOperation.REMOVE_ORPHAN_FILES: "rof",
}


def spark_application_name(
    run_id: str, operation: MaintenanceOperation, attempt: int
) -> str:
    """Build a deterministic DNS-1123 label naming one Spark application attempt."""
    if attempt < 1:
        msg = f"attempt must be >= 1, got {attempt}"
        raise ValueError(msg)
    short_id = "".join(c for c in run_id.lower() if c.isalnum())[:20]
    return f"tm-{_CODES[operation]}-{short_id}-a{attempt}"
