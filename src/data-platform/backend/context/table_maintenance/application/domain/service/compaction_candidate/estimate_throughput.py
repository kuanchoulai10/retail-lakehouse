"""Define the estimate_throughput domain service."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_run import OperationRunStatus

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRun

REWRITTEN_BYTES_METRIC = "rewritten_bytes_count"
_HOUR = timedelta(hours=1)


def estimate_throughput(
    runs: Sequence[TableMaintenanceRun],
    *,
    default_bytes_per_hour: float,
    max_samples: int = 10,
) -> float:
    """Return how many bytes per hour compaction of a table rewrites, from its past runs.

    The newest ``max_samples`` succeeded compactions that rewrote some bytes and
    whose succeeded attempt has a start and an end count: the sum of their bytes
    over the sum of those attempts' hours. A compaction whose result was never
    reported (no bytes), one that rewrote nothing, and an attempt without a
    duration are left out. Without any such compaction, ``default_bytes_per_hour``.
    """
    if default_bytes_per_hour <= 0:
        raise ValueError(f"the default throughput must be positive, got {default_bytes_per_hour}")
    samples = sorted(_samples(runs), key=lambda s: s[0], reverse=True)[:max_samples]
    total_bytes = sum(b for _, b, _ in samples)
    total_hours = sum(h for _, _, h in samples)
    if total_bytes <= 0 or total_hours <= 0:
        return default_bytes_per_hour
    return total_bytes / total_hours


def _samples(runs: Sequence[TableMaintenanceRun]) -> list[tuple[datetime, int, float]]:
    """Return (finished at, bytes, hours) of every usable succeeded compaction."""
    found: list[tuple[datetime, int, float]] = []
    for run in runs:
        for operation in run.operations:
            if operation.operation is not MaintenanceOperation.REWRITE_DATA_FILES:
                continue
            if operation.status is not OperationRunStatus.SUCCEEDED:
                continue
            rewritten = operation.metrics.get(REWRITTEN_BYTES_METRIC, 0)
            attempt = next(
                (a for a in operation.attempt_history if a.status is OperationRunStatus.SUCCEEDED),
                None,
            )
            if rewritten <= 0 or attempt is None or attempt.finished_at is None:
                continue
            hours = (attempt.finished_at - attempt.started_at) / _HOUR
            if hours > 0:
                found.append((attempt.finished_at, rewritten, hours))
    return found
