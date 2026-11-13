"""Tests for the CompactionCandidate aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    CompactionCandidateId,
    HoldReason,
    InvalidCandidateTransition,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
LATER = NOW + timedelta(minutes=5)
TABLE = TableId("t-1")
KEY = PartitionKey(spec_id=0, values=("eu",))
RUN = TableMaintenanceRunId("run-1")
OTHER_RUN = TableMaintenanceRunId("run-2")
SCORE = CandidateScore(reducible_files=10, data_bytes=1000, estimated_gb_hours=0.1, score=0.6)
NEW_SCORE = CandidateScore(reducible_files=12, data_bytes=1200, estimated_gb_hours=0.12, score=0.65)
LEASE = NOW + timedelta(hours=1)


def _candidate(hold: HoldReason | None = None) -> CompactionCandidate:
    return CompactionCandidate.create(
        table_uuid=TABLE,
        partition=KEY,
        label="region=eu",
        score=SCORE,
        last_written_at=NOW - timedelta(hours=1),
        hold_reason=hold,
        now=NOW,
    )


def _claimed() -> CompactionCandidate:
    candidate = _candidate()
    candidate.claim(RUN, LEASE, NOW)
    return candidate


def _running() -> CompactionCandidate:
    candidate = _claimed()
    candidate.start(RUN, NOW)
    return candidate


def test_new_candidate_is_pending():
    """A partition that qualifies and is not filtered is pending."""
    candidate = _candidate()
    assert candidate.state is CandidateState.PENDING
    assert candidate.hold_reason is None
    assert candidate.claimed_by_run_id is None
    assert candidate.lease_expires_at is None
    assert candidate.observed_at == candidate.updated_at == NOW


def test_new_filtered_candidate_is_held_with_its_reason():
    """A partition that qualifies but is filtered is held, with why."""
    candidate = _candidate(HoldReason.TOO_SMALL)
    assert candidate.state is CandidateState.HELD
    assert candidate.hold_reason is HoldReason.TOO_SMALL


def test_id_is_derived_from_the_table_and_the_partition():
    """The same table and partition always get the same id; another partition gets another."""
    assert _candidate().id == CompactionCandidateId.for_partition(TABLE, KEY)
    assert CompactionCandidateId.for_partition(TABLE, KEY) != CompactionCandidateId.for_partition(
        TABLE, PartitionKey(spec_id=1, values=("eu",))
    )
    assert CompactionCandidateId.for_partition(TABLE, KEY) != CompactionCandidateId.for_partition(TableId("t-2"), KEY)


def test_claim_takes_a_pending_candidate_for_a_run_under_a_lease():
    """Claiming a pending candidate gives it to the run until the lease ends."""
    candidate = _claimed()
    assert candidate.state is CandidateState.CLAIMED
    assert candidate.claimed_by_run_id == RUN
    assert candidate.lease_expires_at == LEASE


@pytest.mark.parametrize("make", [lambda: _candidate(HoldReason.RECENTLY_WRITTEN), _claimed, _running])
def test_claim_refuses_a_candidate_that_is_not_pending(make):
    """Only a pending candidate can be claimed."""
    with pytest.raises(InvalidCandidateTransition):
        make().claim(OTHER_RUN, LEASE, NOW)


def test_start_moves_a_claimed_candidate_to_running():
    """The first submit of its run starts the candidate."""
    candidate = _running()
    assert candidate.state is CandidateState.RUNNING
    assert candidate.claimed_by_run_id == RUN
    assert candidate.lease_expires_at == LEASE


def test_start_again_by_the_same_run_changes_nothing():
    """A retried submit starts a running candidate again without error."""
    candidate = _running()
    candidate.start(RUN, LATER)
    assert candidate.state is CandidateState.RUNNING


def test_start_by_another_run_is_refused():
    """A candidate claimed by one run cannot be started by another."""
    with pytest.raises(InvalidCandidateTransition):
        _claimed().start(OTHER_RUN, NOW)


def test_start_of_a_pending_candidate_is_refused():
    """A candidate nobody claimed cannot be started."""
    with pytest.raises(InvalidCandidateTransition):
        _candidate().start(RUN, NOW)


@pytest.mark.parametrize(("succeeded", "state"), [(True, CandidateState.DONE), (False, CandidateState.FAILED)])
@pytest.mark.parametrize("make", [_claimed, _running])
def test_finish_ends_the_candidate_of_its_run(make, succeeded, state):
    """The run's end moves its claimed or running candidate to done or failed and ends the lease."""
    candidate = make()
    candidate.finish(RUN, succeeded=succeeded, now=LATER)
    assert candidate.state is state
    assert candidate.claimed_by_run_id == RUN
    assert candidate.lease_expires_at is None
    assert candidate.updated_at == LATER


def test_finish_of_another_run_is_a_no_op():
    """A run that does not hold the candidate cannot end it."""
    candidate = _running()
    candidate.finish(OTHER_RUN, succeeded=True, now=LATER)
    assert candidate.state is CandidateState.RUNNING
    assert candidate.updated_at == NOW


def test_finish_twice_keeps_the_first_outcome():
    """A replayed finish leaves the candidate as the first finish left it."""
    candidate = _running()
    candidate.finish(RUN, succeeded=True, now=LATER)
    candidate.finish(RUN, succeeded=False, now=LATER + timedelta(minutes=1))
    assert candidate.state is CandidateState.DONE


@pytest.mark.parametrize("make", [_claimed, _running])
def test_release_hands_the_candidate_back(make):
    """A run that never ran gives its candidates back as pending."""
    candidate = make()
    candidate.release(RUN, LATER)
    assert candidate.state is CandidateState.PENDING
    assert candidate.claimed_by_run_id is None
    assert candidate.lease_expires_at is None


def test_release_of_a_finished_candidate_changes_nothing():
    """A finished candidate stays finished when its run releases it."""
    candidate = _running()
    candidate.finish(RUN, succeeded=True, now=LATER)
    candidate.release(RUN, LATER)
    assert candidate.state is CandidateState.DONE


def test_release_by_another_run_is_refused():
    """A run cannot release a candidate another run holds."""
    with pytest.raises(InvalidCandidateTransition):
        _claimed().release(OTHER_RUN, LATER)


def test_observe_rescores_a_pending_candidate():
    """A new observation replaces the score and the last write."""
    candidate = _candidate()
    written = NOW - timedelta(minutes=1)
    candidate.observe(NEW_SCORE, written, None, LATER)
    assert candidate.state is CandidateState.PENDING
    assert candidate.score == NEW_SCORE
    assert candidate.last_written_at == written
    assert candidate.observed_at == candidate.updated_at == LATER


def test_observe_holds_a_pending_candidate_and_lifts_the_hold():
    """A filter that now applies holds the candidate; once it no longer applies it is pending again."""
    candidate = _candidate()
    candidate.observe(NEW_SCORE, NOW, HoldReason.RECENTLY_WRITTEN, LATER, waiting_since=LATER)
    assert candidate.state is CandidateState.HELD
    assert candidate.hold_reason is HoldReason.RECENTLY_WRITTEN
    assert candidate.waiting_since == LATER
    candidate.observe(NEW_SCORE, NOW, None, LATER + timedelta(minutes=5))
    assert candidate.state is CandidateState.PENDING
    assert candidate.hold_reason is None
    assert candidate.waiting_since is None


@pytest.mark.parametrize("succeeded", [True, False])
def test_observe_turns_a_finished_candidate_pending_again(succeeded):
    """A partition still unhealthy after its run is pending again, whatever the run reported."""
    candidate = _running()
    candidate.finish(RUN, succeeded=succeeded, now=LATER)
    candidate.observe(NEW_SCORE, NOW, None, LATER + timedelta(minutes=1))
    assert candidate.state is CandidateState.PENDING
    assert candidate.claimed_by_run_id is None
    assert candidate.score == NEW_SCORE


@pytest.mark.parametrize("make", [_claimed, _running])
def test_observe_keeps_a_claim_with_a_live_lease(make):
    """A claimed or running candidate under a live lease keeps its claim and only takes the new score."""
    candidate = make()
    state = candidate.state
    candidate.observe(NEW_SCORE, NOW, HoldReason.RECENTLY_WRITTEN, LATER, waiting_since=LATER)
    assert candidate.state is state
    assert candidate.claimed_by_run_id == RUN
    assert candidate.lease_expires_at == LEASE
    assert candidate.hold_reason is None
    assert candidate.score == NEW_SCORE


@pytest.mark.parametrize("make", [_claimed, _running])
def test_observe_frees_a_claim_whose_lease_expired(make):
    """A claim past its lease is given up: the candidate is pending (or held) again."""
    candidate = make()
    candidate.observe(NEW_SCORE, NOW, None, LEASE)
    assert candidate.state is CandidateState.PENDING
    assert candidate.claimed_by_run_id is None
    assert candidate.lease_expires_at is None


def test_claim_ends_the_wait_for_a_quiet_period():
    """Once claimed, a candidate no longer counts how long it waited for writes to stop."""
    candidate = _candidate()
    candidate.observe(SCORE, NOW, None, NOW, waiting_since=NOW - timedelta(hours=2))
    assert candidate.waiting_since == NOW - timedelta(hours=2)
    candidate.claim(RUN, LEASE, NOW)
    assert candidate.waiting_since is None


def test_lease_must_end_after_the_claim():
    """A lease that is already over when claimed is refused."""
    with pytest.raises(InvalidCandidateTransition):
        _candidate().claim(RUN, NOW, NOW)


@pytest.mark.parametrize(
    "fields",
    [
        {"state": CandidateState.HELD, "hold_reason": None},
        {"state": CandidateState.PENDING, "hold_reason": HoldReason.TOO_SMALL},
        {"state": CandidateState.CLAIMED, "claimed_by_run_id": None, "lease_expires_at": LEASE},
        {"state": CandidateState.CLAIMED, "claimed_by_run_id": RUN, "lease_expires_at": None},
        {"state": CandidateState.PENDING, "claimed_by_run_id": RUN},
        {"state": CandidateState.DONE, "claimed_by_run_id": None},
        {"state": CandidateState.DONE, "claimed_by_run_id": RUN, "lease_expires_at": LEASE},
    ],
)
def test_combinations_that_cannot_happen_are_refused(fields):
    """The state, hold reason, claim and lease always agree."""
    base: dict[str, Any] = {
        "id": CompactionCandidateId.for_partition(TABLE, KEY),
        "table_uuid": TABLE,
        "partition": KEY,
        "label": "region=eu",
        "state": CandidateState.PENDING,
        "score": SCORE,
        "observed_at": NOW,
        "updated_at": NOW,
    }
    with pytest.raises(ValidationError):
        CompactionCandidate(**{**base, **fields})
