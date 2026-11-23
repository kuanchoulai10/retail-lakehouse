"""Define the spark_application_name function."""

from __future__ import annotations

from context.table_maintenance.application.port.outbound.table_maintenance_run import TableMaintenanceRunId

_CODES: dict[str, str] = {
    "rewrite_data_files": "rdf",
    "rewrite_manifests": "rm",
    "expire_snapshots": "es",
    "remove_orphan_files": "rof",
}


def spark_application_name(run_id: str, operation: str, attempt: int) -> str:
    """Build a deterministic DNS-1123 label naming one Spark application attempt.

    The name is ``tm-<operation code>-<suffix>-a<attempt>``, the suffix being the 26 characters after the run
    id's prefix (docs/adr/0011), so two runs minted in the same millisecond still get different names. A
    ``run_id`` that is not a ``TableMaintenanceRunId`` raises ``InvariantViolation``.
    """
    if attempt < 1:
        msg = f"attempt must be >= 1, got {attempt}"
        raise ValueError(msg)
    if operation not in _CODES:
        msg = f"unknown maintenance operation {operation!r}"
        raise ValueError(msg)
    return f"tm-{_CODES[operation]}-{TableMaintenanceRunId(run_id).suffix}-a{attempt}"
