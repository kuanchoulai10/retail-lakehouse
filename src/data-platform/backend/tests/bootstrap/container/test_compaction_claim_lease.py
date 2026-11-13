"""Test how long a run holds the compaction candidates it claims."""

from __future__ import annotations

from datetime import timedelta

from bootstrap.container import compaction_claim_lease
from tests.bootstrap.container.container_support import sqlite_settings


def test_claim_lease_outlives_the_worst_case_of_one_operation_by_an_hour():
    """Three attempts at the deadline, each fenced for 15 minutes, the backoffs, and one hour more."""
    lease = compaction_claim_lease(sqlite_settings(maintenance_attempt_deadline_seconds=600))

    assert lease == 3 * timedelta(minutes=25) + timedelta(minutes=3) + timedelta(hours=1)
