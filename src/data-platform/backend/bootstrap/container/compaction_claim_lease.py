"""Provide the compaction_claim_lease function."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import TableMaintenanceAttemptPolicy

if TYPE_CHECKING:
    from bootstrap.configs import AppSettings

_MARGIN = timedelta(hours=1)


def compaction_claim_lease(settings: AppSettings) -> timedelta:
    """Return how long a run holds the compaction candidates it claims.

    Compaction runs first in a run, so its candidates are done once compaction
    is: the lease outlives the worst case of one operation at the configured
    queue wait limit, attempt deadline and attempts (every attempt waiting out the
    queue, timing out and being fenced, plus the backoffs) by one hour. A run that
    ends earlier hands its candidates back itself; the lease only frees the
    candidates of a run that never reported.
    """
    policy = TableMaintenanceAttemptPolicy(
        max_attempts=settings.maintenance_max_attempts,
        attempt_deadline=timedelta(seconds=settings.maintenance_attempt_deadline_seconds),
        queue_wait_limit=timedelta(seconds=settings.maintenance_queue_wait_limit_seconds),
    )
    return policy.operation_worst_case() + _MARGIN
