"""Test the CompactionRoundActivityPolicy."""

from __future__ import annotations

from datetime import timedelta

from temporalio.common import RetryPolicy

from context.table_maintenance.adapter.hybrid.temporal.inbound.workflows import CompactionRoundActivityPolicy


def test_the_retry_policy_is_the_one_rounds_have_run_with():
    """Five attempts, backing off from 2 s by doubling, as every recorded round history used."""
    assert CompactionRoundActivityPolicy().retry_policy() == RetryPolicy(
        maximum_attempts=5, initial_interval=timedelta(seconds=2), backoff_coefficient=2.0
    )


def test_the_worst_case_is_every_attempt_of_the_round_then_of_a_signal_timing_out():
    """Five 2-minute round attempts and 30 s of backoff, then five 30 s signal attempts and 30 s of backoff."""
    policy = CompactionRoundActivityPolicy()

    assert policy.worst_case() == 5 * timedelta(minutes=2) + timedelta(seconds=30) + 5 * timedelta(
        seconds=30
    ) + timedelta(seconds=30)


def test_the_worst_case_follows_the_attempts_and_timeouts():
    """Fewer attempts and shorter timeouts shorten it: two attempts back off once."""
    policy = CompactionRoundActivityPolicy(
        round_timeout=timedelta(seconds=10), signal_timeout=timedelta(seconds=5), max_attempts=2
    )

    assert policy.worst_case() == timedelta(seconds=2 * 10 + 2 + 2 * 5 + 2)
