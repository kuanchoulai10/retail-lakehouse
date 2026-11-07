"""Test the TableMaintenanceAttemptPolicy."""

from __future__ import annotations

from datetime import timedelta

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableMaintenanceAttemptPolicy,
)


def test_default_policy_matches_the_maintenance_workflow_defaults():
    """The default policy has three attempts, the default deadline and a 60 second first backoff."""
    policy = TableMaintenanceAttemptPolicy()
    assert policy.max_attempts == 3
    assert policy.attempt_deadline == timedelta(seconds=DEFAULT_ATTEMPT_DEADLINE_SECONDS)
    assert policy.backoff_after(1) == timedelta(seconds=60)
    assert policy.backoff_after(2) == timedelta(seconds=120)


def test_operation_worst_case_is_every_attempt_timing_out_plus_backoffs():
    """The worst case of an operation is every attempt hitting its deadline plus all the backoffs."""
    policy = TableMaintenanceAttemptPolicy()
    assert policy.operation_worst_case() == timedelta(seconds=3 * 21600 + 180)
    short = TableMaintenanceAttemptPolicy(attempt_deadline=timedelta(minutes=10))
    assert short.operation_worst_case() == timedelta(minutes=33)
