"""Test the MaintenanceAttemptPolicy."""

from __future__ import annotations

from datetime import timedelta

from adapter.inbound.temporal.workflows import MaintenanceAttemptPolicy
from adapter.temporal_contracts import DEFAULT_ATTEMPT_DEADLINE_SECONDS


def test_default_policy_matches_the_maintenance_workflow_defaults():
    policy = MaintenanceAttemptPolicy()
    assert policy.max_attempts == 3
    assert policy.attempt_deadline == timedelta(
        seconds=DEFAULT_ATTEMPT_DEADLINE_SECONDS
    )
    assert policy.backoff_after(1) == timedelta(seconds=60)
    assert policy.backoff_after(2) == timedelta(seconds=120)


def test_operation_worst_case_is_every_attempt_timing_out_plus_backoffs():
    policy = MaintenanceAttemptPolicy()
    assert policy.operation_worst_case() == timedelta(seconds=3 * 21600 + 180)
    short = MaintenanceAttemptPolicy(attempt_deadline=timedelta(minutes=10))
    assert short.operation_worst_case() == timedelta(minutes=33)
