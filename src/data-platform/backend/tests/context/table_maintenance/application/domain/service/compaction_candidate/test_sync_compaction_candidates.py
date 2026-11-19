"""Tests for the sync_compaction_candidates domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateFilters,
    CandidateScoring,
    CandidateState,
    CompactionCandidate,
    HoldReason,
    ObservedPartition,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.domain.service.compaction_candidate import (
    sync_compaction_candidates,
)

ROUND_1 = "cr-00000000000000000000000001"

RUN_1 = "mr-00000000000000000000000001"

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
TABLE = TableId("t-1")
RUN = TableMaintenanceRunId(RUN_1)
GIB = 1024**3
FILTERS = CandidateFilters(min_partition_bytes=1000, quiet_seconds=120, max_quiet_wait_seconds=3600)
LONG_AGO = NOW - timedelta(hours=2)


def _observed(
    value: str,
    *,
    reducible: int = 10,
    data_bytes: int = 10_000,
    written: datetime | None = LONG_AGO,
) -> ObservedPartition:
    return ObservedPartition(
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"region={value}",
        reducible_files=reducible,
        data_bytes=data_bytes,
        last_written_at=written,
    )


def _sync(existing, observed, *, now: datetime = NOW):  # noqa: ANN202
    return sync_compaction_candidates(
        TABLE,
        existing,
        observed,
        scoring=CandidateScoring(),
        filters=FILTERS,
        memory_gb=1.5,
        throughput_bytes_per_hour=2 * GIB,
        now=now,
    )


def _by_value(candidates) -> dict[str, CompactionCandidate]:  # noqa: ANN001
    return {str(c.partition.values[0]): c for c in candidates}


def test_new_qualifying_partition_becomes_pending():
    """A partition seen to need compaction for the first time is a new pending candidate."""
    result = _sync([], [_observed("eu")])

    (candidate,) = result.saved
    assert candidate.state is CandidateState.PENDING
    assert candidate.table_uuid == TABLE
    assert candidate.label == "region=eu"
    assert candidate.score.reducible_files == 10
    assert candidate.observed_at == NOW
    assert result.removed == ()
    assert result.next_check_at is None


def test_partition_no_longer_qualifying_is_removed():
    """A partition the observation no longer finds in need of compaction leaves the candidates."""
    first = _sync([], [_observed("eu"), _observed("us")])

    result = _sync(list(first.saved), [_observed("us")], now=NOW + timedelta(minutes=5))

    assert [c.partition.values for c in result.saved] == [("us",)]
    assert result.removed == (_by_value(first.saved)["eu"].id,)


def test_done_candidate_still_qualifying_is_pending_again():
    """Spark said done, but the table still needs compaction there: the candidate is pending with a fresh score."""
    (candidate,) = _sync([], [_observed("eu")]).saved
    candidate.grant(ROUND_1, NOW + timedelta(minutes=10), NOW)
    candidate.claim(RUN, NOW + timedelta(hours=1), NOW)
    candidate.start(RUN, NOW)
    candidate.finish(RUN, succeeded=True, now=NOW + timedelta(minutes=10))

    result = _sync([candidate], [_observed("eu", reducible=4)], now=NOW + timedelta(minutes=15))

    (again,) = result.saved
    assert again.state is CandidateState.PENDING
    assert again.claimed_by_run_id is None
    assert again.score.reducible_files == 4


def test_small_partition_is_held_too_small():
    """A partition with less data than the minimum is held as too small."""
    result = _sync([], [_observed("eu", data_bytes=999), _observed("us", data_bytes=1000)])

    by_value = _by_value(result.saved)
    assert by_value["eu"].state is CandidateState.HELD
    assert by_value["eu"].hold_reason is HoldReason.TOO_SMALL
    assert by_value["us"].state is CandidateState.PENDING


def test_recent_partition_is_held_and_sets_next_check():
    """A partition written within the quiet period is held, and the hold ends when the period does."""
    written = NOW - timedelta(seconds=30)
    result = _sync([], [_observed("eu", written=written), _observed("us", written=NOW - timedelta(seconds=100))])

    by_value = _by_value(result.saved)
    assert by_value["eu"].hold_reason is HoldReason.RECENTLY_WRITTEN
    assert by_value["us"].hold_reason is HoldReason.RECENTLY_WRITTEN
    assert result.next_check_at == NOW + timedelta(seconds=20)


def test_recent_hold_ends_after_the_quiet_period():
    """Once no write has landed for the quiet period, the held partition is pending."""
    written = NOW - timedelta(seconds=30)
    first = _sync([], [_observed("eu", written=written)])

    result = _sync(list(first.saved), [_observed("eu", written=written)], now=NOW + timedelta(seconds=90))

    (candidate,) = result.saved
    assert candidate.state is CandidateState.PENDING
    assert candidate.waiting_since is None
    assert result.next_check_at is None


def test_partition_written_without_pause_is_held_at_most_the_longest_wait():
    """A partition written every minute is held only up to the longest wait, then it is pending."""
    first = _sync([], [_observed("eu", written=NOW - timedelta(seconds=10))])
    (held,) = first.saved
    assert held.waiting_since == NOW

    later = NOW + timedelta(seconds=3599)
    still = _sync([held], [_observed("eu", written=later - timedelta(seconds=10))], now=later)
    (candidate,) = still.saved
    assert candidate.hold_reason is HoldReason.RECENTLY_WRITTEN
    assert still.next_check_at == NOW + timedelta(seconds=3600)

    past = NOW + timedelta(seconds=3600)
    released = _sync([candidate], [_observed("eu", written=past - timedelta(seconds=10))], now=past)
    (candidate,) = released.saved
    assert candidate.state is CandidateState.PENDING
    assert candidate.waiting_since == NOW

    on = past + timedelta(minutes=5)
    stays = _sync([candidate], [_observed("eu", written=on - timedelta(seconds=10))], now=on)
    assert stays.saved[0].state is CandidateState.PENDING


def test_unknown_last_write_is_not_recent():
    """A partition whose last write is unknown is not held as recently written."""
    result = _sync([], [_observed("eu", written=None)])
    assert result.saved[0].state is CandidateState.PENDING


def test_claimed_candidate_with_live_lease_keeps_its_claim():
    """A candidate a run holds under a live lease keeps its claim, even when a filter would now hold it."""
    (candidate,) = _sync([], [_observed("eu")]).saved
    candidate.grant(ROUND_1, NOW + timedelta(minutes=10), NOW)
    candidate.claim(RUN, NOW + timedelta(hours=1), NOW)

    result = _sync([candidate], [_observed("eu", written=NOW, reducible=12)], now=NOW + timedelta(minutes=1))

    (kept,) = result.saved
    assert kept.state is CandidateState.CLAIMED
    assert kept.claimed_by_run_id == RUN
    assert kept.score.reducible_files == 12
    assert result.next_check_at is None


def test_claimed_candidate_with_expired_lease_is_pending_again():
    """A claim past its lease is given up at the next observation."""
    (candidate,) = _sync([], [_observed("eu")]).saved
    candidate.grant(ROUND_1, NOW + timedelta(minutes=10), NOW)
    candidate.claim(RUN, NOW + timedelta(hours=1), NOW)

    result = _sync([candidate], [_observed("eu")], now=NOW + timedelta(hours=1))

    assert result.saved[0].state is CandidateState.PENDING
    assert result.saved[0].claimed_by_run_id is None


@pytest.mark.parametrize("quiet", [0, 120])
def test_nothing_is_held_without_a_minimum_size_once_the_quiet_period_passed(quiet):
    """Without a minimum size an empty partition is not small; a write one quiet period ago is not recent."""
    filters = CandidateFilters(min_partition_bytes=0, quiet_seconds=quiet, max_quiet_wait_seconds=3600)
    result = sync_compaction_candidates(
        TABLE,
        [],
        [_observed("eu", data_bytes=0, written=NOW - timedelta(seconds=quiet))],
        scoring=CandidateScoring(),
        filters=filters,
        memory_gb=1.5,
        throughput_bytes_per_hour=2 * GIB,
        now=NOW,
    )
    assert result.saved[0].state is CandidateState.PENDING
