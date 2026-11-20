"""Test the TableMaintenanceAttemptPolicy."""

from __future__ import annotations

from datetime import timedelta

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    DEFAULT_ATTEMPT_DEADLINE_SECONDS,
    DEFAULT_QUEUE_WAIT_LIMIT_SECONDS,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import (
    TableMaintenanceAttemptPolicy,
    TableMaintenanceFencingPolicy,
)

DEFAULT_PER_ATTEMPT = timedelta(seconds=86400 + 21600 + 900)


def test_default_policy_matches_the_maintenance_workflow_defaults():
    """The default policy has three attempts, the default deadline and queue wait limit, and a 60 s first backoff."""
    policy = TableMaintenanceAttemptPolicy()
    assert policy.max_attempts == 3
    assert policy.attempt_deadline == timedelta(seconds=DEFAULT_ATTEMPT_DEADLINE_SECONDS)
    assert policy.queue_wait_limit == timedelta(seconds=DEFAULT_QUEUE_WAIT_LIMIT_SECONDS)
    assert DEFAULT_QUEUE_WAIT_LIMIT_SECONDS == 86400
    assert policy.backoff_after(1) == timedelta(seconds=60)
    assert policy.backoff_after(2) == timedelta(seconds=120)


def test_operation_worst_case_is_every_attempt_waiting_timing_out_and_fenced_plus_backoffs():
    """The worst case is every attempt waiting out the queue limit, its deadline and its fence, plus the backoffs."""
    policy = TableMaintenanceAttemptPolicy()
    assert policy.operation_worst_case() == DEFAULT_PER_ATTEMPT * 3 + timedelta(seconds=180)
    short = TableMaintenanceAttemptPolicy(attempt_deadline=timedelta(minutes=10), queue_wait_limit=timedelta(minutes=5))
    assert short.operation_worst_case() == timedelta(minutes=3 * 30 + 3)


def test_worst_case_counts_the_queue_wait():
    """A queue wait limit adds to every attempt of the worst case."""
    policy = TableMaintenanceAttemptPolicy(
        max_attempts=3, attempt_deadline=timedelta(hours=6), queue_wait_limit=timedelta(hours=24)
    )
    assert policy.operation_worst_case() == (timedelta(hours=30, minutes=15)) * 3 + timedelta(seconds=180)


def test_default_fencing_polls_and_bounds_the_wait():
    """A timed-out attempt is polled every 30 s, bounded at 15 min, then polled every 5 min; it renews no lease."""
    fencing = TableMaintenanceFencingPolicy()
    assert fencing.poll_interval == timedelta(seconds=30)
    assert not hasattr(fencing, "renew_interval")
    assert fencing.confirm_bound == timedelta(minutes=15)
    assert fencing.slow_poll_interval == timedelta(minutes=5)
    assert TableMaintenanceAttemptPolicy().fencing == fencing


def test_unfenced_worst_case_is_the_bound_from_before_fencing():
    """The unfenced worst case is every attempt hitting its deadline plus the backoffs, as before fencing existed."""
    assert TableMaintenanceAttemptPolicy().unfenced_operation_worst_case() == timedelta(seconds=3 * 21600 + 180)


def test_backoff_beyond_the_listed_ones_repeats_the_last():
    """With more attempts than listed backoffs, every later failed attempt sleeps the last backoff."""
    policy = TableMaintenanceAttemptPolicy(max_attempts=5)
    assert [policy.backoff_after(n) for n in range(1, 5)] == [timedelta(seconds=s) for s in (60, 120, 120, 120)]


def test_worst_case_counts_one_backoff_between_each_pair_of_attempts():
    """The worst case sleeps after every attempt but the last, so it follows the number of attempts."""
    assert TableMaintenanceAttemptPolicy(max_attempts=5).operation_worst_case() == DEFAULT_PER_ATTEMPT * 5 + timedelta(
        seconds=60 + 120 + 120 + 120
    )
    assert TableMaintenanceAttemptPolicy(max_attempts=1).operation_worst_case() == DEFAULT_PER_ATTEMPT
    assert TableMaintenanceAttemptPolicy(max_attempts=5).unfenced_operation_worst_case() == timedelta(
        seconds=5 * 21600 + 60 + 120 + 120 + 120
    )
