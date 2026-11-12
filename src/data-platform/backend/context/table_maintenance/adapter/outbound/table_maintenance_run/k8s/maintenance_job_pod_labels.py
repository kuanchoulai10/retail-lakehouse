"""Define the maintenance_job_pod_labels function."""

from __future__ import annotations


def maintenance_job_pod_labels(run_id: str, operation: str, attempt: int) -> dict[str, str]:
    """Return the labels that tie a SparkApplication and its pods to one operation attempt."""
    return {
        "table-maintenance/run-id": run_id,
        "table-maintenance/operation": operation,
        "table-maintenance/attempt": str(attempt),
    }
