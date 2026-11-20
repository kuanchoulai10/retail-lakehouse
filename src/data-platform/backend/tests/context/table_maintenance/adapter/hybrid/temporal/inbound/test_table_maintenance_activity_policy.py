"""Test the TableMaintenanceActivityPolicy."""

from __future__ import annotations

from datetime import timedelta

from temporalio.common import RetryPolicy

from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import TableMaintenanceActivityPolicy


def test_the_retry_policy_is_the_one_maintenance_runs_have_run_with():
    """Five attempts, backing off from 2 s by doubling, as every recorded maintenance history used."""
    assert TableMaintenanceActivityPolicy().retry_policy() == RetryPolicy(
        maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0
    )


def test_the_worst_case_is_every_attempt_timing_out():
    """Five 2-minute attempts and 2 + 4 + 8 + 16 s of backoff."""
    assert TableMaintenanceActivityPolicy().worst_case() == 5 * timedelta(minutes=2) + timedelta(seconds=30)


def test_the_worst_case_follows_the_attempts_and_timeout():
    """Fewer attempts and a shorter timeout shorten it: two attempts back off once."""
    policy = TableMaintenanceActivityPolicy(start_to_close=timedelta(seconds=10), max_attempts=2)

    assert policy.worst_case() == timedelta(seconds=2 * 10 + 2)
