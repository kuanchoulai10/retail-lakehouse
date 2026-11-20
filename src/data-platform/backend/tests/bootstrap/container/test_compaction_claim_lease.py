"""Test how long a run holds the compaction candidates it claims."""

from __future__ import annotations

from datetime import timedelta

from bootstrap.container import compaction_claim_lease
from tests.bootstrap.container.container_support import sqlite_settings


def test_claim_lease_outlives_the_worst_case_of_one_operation_by_an_hour():
    """Three attempts at the queue wait limit and deadline, each fenced for 15 minutes, the backoffs, and one hour."""
    lease = compaction_claim_lease(
        sqlite_settings(maintenance_attempt_deadline_seconds=600, maintenance_queue_wait_limit_seconds=300)
    )

    assert lease == 3 * timedelta(minutes=30) + timedelta(minutes=3) + timedelta(hours=1)


def test_claim_lease_follows_the_configured_attempts():
    """With five attempts the worst case counts five queue waits, deadlines and fencing bounds, and four backoffs."""
    lease = compaction_claim_lease(
        sqlite_settings(
            maintenance_attempt_deadline_seconds=600,
            maintenance_max_attempts=5,
            maintenance_queue_wait_limit_seconds=300,
        )
    )

    assert lease == 5 * timedelta(minutes=30) + timedelta(seconds=60 + 120 + 120 + 120) + timedelta(hours=1)
