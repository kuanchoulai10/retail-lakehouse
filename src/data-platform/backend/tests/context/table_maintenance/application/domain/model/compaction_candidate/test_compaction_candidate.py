"""Tests for the CompactionCandidate aggregate."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from base import InvariantViolation
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
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from shared_kernel import prefixed_id_pattern

RUN_1 = "mr-00000000000000000000000001"
RUN_2 = "mr-00000000000000000000000002"
CANDIDATE_ID = "cc-00000000000000000000000001"
CANDIDATE_ID_SHAPE = prefixed_id_pattern("cc")

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
LATER = NOW + timedelta(minutes=5)
TABLE = TableId("t-1")
KEY = PartitionKey(spec_id=0, values=("eu",))
RUN = TableMaintenanceRunId(RUN_1)
OTHER_RUN = TableMaintenanceRunId(RUN_2)
SCORE = CandidateScore(reducible_files=10, data_bytes=1000, estimated_gb_hours=0.1, score=0.6)
NEW_SCORE = CandidateScore(reducible_files=12, data_bytes=1200, estimated_gb_hours=0.12, score=0.65)
LEASE = NOW + timedelta(hours=1)
ROUND = "cr-00000000000000000000000001"
OTHER_ROUND = "cr-00000000000000000000000002"
GRANT_LEASE = NOW + timedelta(minutes=10)
SLA = {
    MaintenancePriority.P0: timedelta(hours=1),
    MaintenancePriority.P1: timedelta(hours=4),
    MaintenancePriority.P2: timedelta(hours=8),
}


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


def _granted() -> CompactionCandidate:
    candidate = _candidate()
    candidate.grant(ROUND, GRANT_LEASE, NOW)
    return candidate


def _claimed() -> CompactionCandidate:
    candidate = _granted()
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


def test_new_candidate_gets_a_cc_id():
    """A new candidate gets a fresh random ``cc-`` id; the store keeps one per table and partition."""
    first, second = _candidate(), _candidate()
    assert CANDIDATE_ID_SHAPE.fullmatch(first.id.value)
    assert first.id != second.id


def test_claim_takes_a_granted_candidate_for_a_run_under_a_lease():
    """Claiming a granted candidate gives it to the run until the lease ends, and keeps the round that granted it."""
    candidate = _claimed()
    assert candidate.state is CandidateState.CLAIMED
    assert candidate.claimed_by_run_id == RUN
    assert candidate.lease_expires_at == LEASE
    assert candidate.granted_round_id == ROUND


@pytest.mark.parametrize("make", [_candidate, lambda: _candidate(HoldReason.RECENTLY_WRITTEN), _claimed, _running])
def test_claim_needs_a_grant(make):
    """Only a candidate a compaction round granted can be claimed."""
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
    candidate.grant(ROUND, GRANT_LEASE, NOW)
    candidate.claim(RUN, LEASE, NOW)
    assert candidate.waiting_since is None


def test_lease_must_end_after_the_claim():
    """A lease that is already over when claimed is refused."""
    with pytest.raises(InvalidCandidateTransition):
        _granted().claim(RUN, NOW, NOW)


def test_claim_refuses_a_grant_whose_lease_ended():
    """A grant past its lease is no longer the run's to take."""
    with pytest.raises(InvalidCandidateTransition):
        _granted().claim(RUN, GRANT_LEASE + timedelta(hours=1), GRANT_LEASE)


def test_grant_moves_pending_to_granted_with_a_lease():
    """A round grants a pending candidate until its lease ends, and names itself."""
    candidate = _granted()
    assert candidate.state is CandidateState.GRANTED
    assert candidate.granted_round_id == ROUND
    assert candidate.lease_expires_at == GRANT_LEASE
    assert candidate.claimed_by_run_id is None
    assert candidate.updated_at == NOW


@pytest.mark.parametrize("make", [lambda: _candidate(HoldReason.TOO_SMALL), _granted, _claimed, _running])
def test_grant_refuses_a_candidate_that_is_not_pending(make):
    """Only a pending candidate can be granted; a held one is filtered, a granted or claimed one is taken."""
    with pytest.raises(InvalidCandidateTransition):
        make().grant(OTHER_ROUND, GRANT_LEASE, NOW)


def test_grant_lease_must_end_after_the_grant():
    """A grant whose lease is already over is refused."""
    with pytest.raises(InvalidCandidateTransition):
        _candidate().grant(ROUND, NOW, NOW)


@pytest.mark.parametrize("hold", [HoldReason.NOT_DUE, HoldReason.COOLDOWN])
def test_observation_keeps_a_live_grant(hold):
    """A granted candidate under a live lease keeps its grant through an observation, even a not-due one."""
    candidate = _granted()
    candidate.observe(NEW_SCORE, NOW, hold, LATER, priority=MaintenancePriority.P0)
    assert candidate.state is CandidateState.GRANTED
    assert candidate.granted_round_id == ROUND
    assert candidate.lease_expires_at == GRANT_LEASE
    assert candidate.score == NEW_SCORE
    assert candidate.priority is MaintenancePriority.P0


@pytest.mark.parametrize("hold", [HoldReason.TOO_SMALL, HoldReason.RECENTLY_WRITTEN])
def test_a_filter_ends_a_live_grant(hold):
    """A granted partition found too small or still being written is held: no run may compact it now."""
    candidate = _granted()
    candidate.observe(NEW_SCORE, LATER, hold, LATER)
    assert candidate.state is CandidateState.HELD
    assert candidate.hold_reason is hold
    assert candidate.granted_round_id is None
    assert candidate.lease_expires_at is None
    assert candidate.pending_since is None


@pytest.mark.parametrize(
    "hold", [HoldReason.TOO_SMALL, HoldReason.RECENTLY_WRITTEN, HoldReason.NOT_DUE, HoldReason.COOLDOWN]
)
def test_a_filter_does_not_end_a_live_claim(hold):
    """A claimed candidate keeps its claim whatever the observation finds: its run may be writing."""
    candidate = _claimed()
    candidate.observe(NEW_SCORE, LATER, hold, LATER)
    assert candidate.state is CandidateState.CLAIMED
    assert candidate.claimed_by_run_id == RUN


def test_observation_returns_an_expired_grant_to_pending():
    """A grant nobody claimed before its lease ended is pending again, for the next round."""
    candidate = _granted()
    candidate.observe(NEW_SCORE, NOW, None, GRANT_LEASE)
    assert candidate.state is CandidateState.PENDING
    assert candidate.granted_round_id is None
    assert candidate.lease_expires_at is None


def test_pending_since_survives_a_grant_and_clears_on_claim():
    """The wait for a round starts when the candidate becomes pending and ends when a run claims it."""
    candidate = _candidate()
    assert candidate.pending_since == NOW
    candidate.observe(NEW_SCORE, NOW, None, LATER)
    assert candidate.pending_since == NOW
    candidate.grant(ROUND, LATER + timedelta(minutes=10), LATER)
    assert candidate.pending_since == NOW
    candidate.observe(NEW_SCORE, NOW, None, LATER + timedelta(minutes=10))
    assert candidate.state is CandidateState.PENDING
    assert candidate.pending_since == NOW
    candidate.grant(ROUND, LATER + timedelta(minutes=30), LATER + timedelta(minutes=20))
    candidate.claim(RUN, LEASE + timedelta(hours=1), LATER + timedelta(minutes=20))
    assert candidate.pending_since is None


def test_a_cooldown_keeps_the_wait_going():
    """A cooldown does not restart the SLA clock: the wait goes on from when the candidate first became pending."""
    candidate = _candidate()
    candidate.observe(NEW_SCORE, NOW, HoldReason.COOLDOWN, LATER)
    assert candidate.state is CandidateState.HELD
    assert candidate.pending_since == NOW
    much_later = NOW + timedelta(hours=9)
    assert not candidate.overdue(SLA, much_later)
    candidate.observe(NEW_SCORE, NOW, None, much_later)
    assert candidate.pending_since == NOW
    assert candidate.overdue(SLA, much_later)


@pytest.mark.parametrize("hold", [HoldReason.TOO_SMALL, HoldReason.RECENTLY_WRITTEN, HoldReason.NOT_DUE])
def test_a_hold_other_than_a_cooldown_ends_the_wait_and_it_restarts_when_pending_again(hold):
    """A partition kept out by a filter, a dry run, compaction off or needing attention is not waiting for a round.

    Its wait restarts once it is pending again, so a week of dry run does not read as a week overdue.
    """
    candidate = _candidate()
    candidate.observe(NEW_SCORE, NOW, hold, LATER)
    assert candidate.pending_since is None
    candidate.observe(NEW_SCORE, NOW, None, LATER + timedelta(minutes=1))
    assert candidate.pending_since == LATER + timedelta(minutes=1)


@pytest.mark.parametrize("hold", [HoldReason.NOT_DUE, HoldReason.COOLDOWN])
def test_a_candidate_created_not_due_starts_its_wait_when_pending(hold):
    """The clock starts when a candidate first becomes pending, not while its table's compaction is not due."""
    candidate = _candidate(hold)
    assert candidate.pending_since is None
    candidate.observe(NEW_SCORE, NOW, None, LATER)
    assert candidate.pending_since == LATER


@pytest.mark.parametrize(
    ("make", "at", "busy"),
    [
        (_candidate, NOW, False),
        (lambda: _candidate(HoldReason.NOT_DUE), NOW, False),
        (_granted, NOW, True),
        (_granted, GRANT_LEASE, False),
        (_claimed, NOW, True),
        (_running, NOW, True),
        (_running, LEASE, False),
    ],
)
def test_keeps_its_table_busy(make, at, busy):
    """A live grant, claim or run occupies the table; pending, held and expired ones do not."""
    assert make().keeps_its_table_busy(at) is busy


@pytest.mark.parametrize("succeeded", [True, False])
def test_a_finished_candidate_keeps_its_table_busy_until_observed(succeeded):
    """A run that just ended leaves its table busy until the next observation decides what is left."""
    candidate = _running()
    candidate.finish(RUN, succeeded=succeeded, now=LATER)
    assert candidate.keeps_its_table_busy(LATER + timedelta(days=1))
    candidate.observe(NEW_SCORE, NOW, None, LATER + timedelta(days=1))
    assert not candidate.keeps_its_table_busy(LATER + timedelta(days=1))


def test_a_new_held_candidate_has_no_pending_since():
    """A candidate created held is not waiting for a round."""
    assert _candidate(HoldReason.TOO_SMALL).pending_since is None


def test_release_hands_a_claim_back_as_pending_not_granted():
    """A run that never started gives its candidates back to the next round, not to its old grant."""
    candidate = _claimed()
    candidate.release(RUN, LATER)
    assert candidate.state is CandidateState.PENDING
    assert candidate.granted_round_id is None
    assert candidate.pending_since == LATER


def test_overdue_after_the_priority_sla():
    """A candidate pending longer than its priority's SLA is overdue; a shorter wait is not."""
    p2 = _candidate()
    assert p2.priority is MaintenancePriority.P2
    assert p2.overdue(SLA, NOW + timedelta(hours=8, seconds=1))
    assert not p2.overdue(SLA, NOW + timedelta(hours=8))
    p0 = CompactionCandidate.create(
        table_uuid=TABLE,
        partition=KEY,
        label="region=eu",
        score=SCORE,
        last_written_at=None,
        hold_reason=None,
        now=NOW,
        priority=MaintenancePriority.P0,
    )
    assert not p0.overdue(SLA, NOW + timedelta(minutes=59))
    assert p0.overdue(SLA, NOW + timedelta(minutes=61))


def test_a_granted_candidate_can_be_overdue_but_a_held_or_claimed_one_cannot():
    """Overdue counts the wait for a round; held and claimed candidates are not waiting for one."""
    much_later = NOW + timedelta(days=2)
    assert _granted().overdue(SLA, much_later)
    assert not _candidate(HoldReason.TOO_SMALL).overdue(SLA, much_later)
    assert not _claimed().overdue(SLA, much_later)


def test_a_pending_candidate_without_pending_since_is_not_overdue():
    """A row stored before the wait was recorded has no start, so it is never overdue."""
    candidate = CompactionCandidate(
        id=CompactionCandidateId(CANDIDATE_ID),
        table_uuid=TABLE,
        partition=KEY,
        label="region=eu",
        state=CandidateState.PENDING,
        score=SCORE,
        observed_at=NOW,
        updated_at=NOW,
    )
    assert candidate.pending_since is None
    assert not candidate.overdue(SLA, NOW + timedelta(days=2))


def test_observe_takes_the_policy_priority():
    """Each observation carries the priority of the policy that applies now."""
    candidate = _candidate()
    candidate.observe(NEW_SCORE, NOW, None, LATER, priority=MaintenancePriority.P1)
    assert candidate.priority is MaintenancePriority.P1


def test_a_new_candidate_has_never_been_saved():
    """Version 0 means not stored yet; the store gives it version 1 on the first save."""
    candidate = _candidate()
    assert candidate.version == 0
    candidate.mark_saved()
    assert candidate.version == 1


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
        {"state": CandidateState.GRANTED, "granted_round_id": None, "lease_expires_at": GRANT_LEASE},
        {"state": CandidateState.GRANTED, "granted_round_id": ROUND, "lease_expires_at": None},
        {
            "state": CandidateState.GRANTED,
            "granted_round_id": ROUND,
            "lease_expires_at": LEASE,
            "claimed_by_run_id": RUN,
        },
        {"state": CandidateState.PENDING, "granted_round_id": ROUND},
        {"state": CandidateState.HELD, "hold_reason": HoldReason.TOO_SMALL, "pending_since": NOW},
        {"state": CandidateState.HELD, "hold_reason": HoldReason.RECENTLY_WRITTEN, "pending_since": NOW},
        {"state": CandidateState.HELD, "hold_reason": HoldReason.NOT_DUE, "pending_since": NOW},
        {"state": CandidateState.PENDING, "version": -1},
    ],
)
def test_combinations_that_cannot_happen_are_refused(fields):
    """The state, hold reason, claim and lease always agree."""
    base: dict[str, Any] = {
        "id": CompactionCandidateId(CANDIDATE_ID),
        "table_uuid": TABLE,
        "partition": KEY,
        "label": "region=eu",
        "state": CandidateState.PENDING,
        "score": SCORE,
        "observed_at": NOW,
        "updated_at": NOW,
    }
    with pytest.raises(InvariantViolation):
        CompactionCandidate(**{**base, **fields})


def test_grant_expired_once_the_lease_ends():
    """A grant whose lease is over is expired; a live grant and any other state are not."""
    assert not _granted().grant_expired(GRANT_LEASE - timedelta(seconds=1))
    assert _granted().grant_expired(GRANT_LEASE)
    assert not _candidate().grant_expired(GRANT_LEASE)
    assert not _claimed().grant_expired(LEASE)
