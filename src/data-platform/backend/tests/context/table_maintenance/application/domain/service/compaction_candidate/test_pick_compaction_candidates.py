"""Tests for the pick_compaction_candidates domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateFilters,
    CandidateSelection,
    CandidateShortfall,
    CandidateState,
    HoldReason,
    ObservedPartition,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.domain.service.compaction_candidate import (
    pick_compaction_candidates,
)

RUN_1 = "mr-00000000000000000000000001"
RUN_2 = "mr-00000000000000000000000002"

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
TABLE = TableId("t-1")
RUN = TableMaintenanceRunId(RUN_1)
OTHER = TableMaintenanceRunId(RUN_2)
LEASE = NOW + timedelta(hours=2)
GRANT_LEASE = NOW + timedelta(minutes=10)
SELECTION = CandidateSelection(partitions_per_run=2, filters=CandidateFilters(quiet_seconds=120))


def _observed(
    value: str, reducible: int = 10, written: datetime | None = None, data_bytes: int = 1000
) -> ObservedPartition:
    return ObservedPartition(
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"region={value}",
        reducible_files=reducible,
        data_bytes=data_bytes,
        last_written_at=written,
    )


def _pick(existing, observed, **overrides: Any):  # noqa: ANN001, ANN202
    arguments: dict[str, Any] = {
        "selection": SELECTION,
        "memory_gb": 1.5,
        "throughput_bytes_per_hour": 1e9,
        "released_runs": frozenset(),
        "pick": True,
        "priority": MaintenancePriority.P2,
        "claim_for": RUN,
        "lease_until": LEASE,
        "now": NOW,
    }
    arguments.update(overrides)
    return pick_compaction_candidates(TABLE, existing, observed, **arguments)


def _values(candidates) -> list[str]:  # noqa: ANN001
    return [str(c.partition.values[0]) for c in candidates]


def _granted(observed, grant: set[str]):  # noqa: ANN001, ANN202
    """Sync a due observation (nothing granted yet), then grant the named partitions as a round would."""
    candidates = list(_pick([], observed, now=NOW - timedelta(minutes=1)).saved)
    for candidate in candidates:
        if candidate.partition.values[0] in grant:
            candidate.grant("round-1", GRANT_LEASE, NOW - timedelta(minutes=1))
    return candidates


def test_due_compaction_without_a_grant_takes_nothing_and_awaits_the_schedule():
    """Pending candidates are left to the next compaction round; nothing is claimed."""
    pick = _pick([], [_observed("a", 6), _observed("b", 9)])

    assert pick.selected == ()
    assert pick.shortfall is CandidateShortfall.AWAITING_SCHEDULE
    assert pick.next_eligible_at is None
    assert {c.state for c in pick.saved} == {CandidateState.PENDING}


def test_due_compaction_claims_its_granted_candidates_only():
    """The granted candidates are claimed for the run, best first; a pending one stays pending."""
    observed = [_observed("a", 6), _observed("b", 9), _observed("c", 8)]
    pick = _pick(_granted(observed, {"a", "b"}), observed)

    assert _values(pick.selected) == ["b", "a"]
    assert {c.state for c in pick.selected} == {CandidateState.CLAIMED}
    assert {c.claimed_by_run_id for c in pick.selected} == {RUN}
    assert {c.granted_round_id for c in pick.selected} == {"round-1"}
    assert [c.state for c in pick.saved if _values([c]) == ["c"]] == [CandidateState.PENDING]
    assert pick.shortfall is None


def test_granted_beyond_partitions_per_run_take_the_best():
    """A run takes at most its share of the grants, the best ones; the others stay granted."""
    observed = [_observed("a", 6), _observed("b", 9), _observed("c", 8)]
    pick = _pick(_granted(observed, {"a", "b", "c"}), observed)

    assert _values(pick.selected) == ["b", "c"]
    assert [c.state for c in pick.saved if _values([c]) == ["a"]] == [CandidateState.GRANTED]


def test_picks_granted_without_claiming_when_no_run_is_named():
    """Without a run to claim for, the granted candidates are picked but stay granted."""
    observed = [_observed("a", 6), _observed("b", 9)]
    pick = _pick(_granted(observed, {"a", "b"}), observed, claim_for=None)

    assert _values(pick.selected) == ["b", "a"]
    assert {c.state for c in pick.saved} == {CandidateState.GRANTED}


def test_not_due_compaction_holds_candidates_not_due():
    """When compaction is not due its candidates are held not due; a filter's reason comes first."""
    selection = CandidateSelection(
        partitions_per_run=2, filters=CandidateFilters(quiet_seconds=120, min_partition_bytes=100)
    )
    pick = _pick([], [_observed("a"), _observed("b", data_bytes=10)], pick=False, selection=selection)

    assert pick.selected == ()
    assert pick.shortfall is None
    reasons = {_values([c])[0]: c.hold_reason for c in pick.saved}
    assert reasons == {"a": HoldReason.NOT_DUE, "b": HoldReason.TOO_SMALL}
    assert {c.state for c in pick.saved} == {CandidateState.HELD}


def test_a_cooling_down_compaction_holds_candidates_in_cooldown():
    """When compaction waits out its cooldown its candidates say so, so their wait for a round goes on."""
    selection = CandidateSelection(
        partitions_per_run=2, filters=CandidateFilters(quiet_seconds=120, min_partition_bytes=100)
    )
    pick = _pick(
        [], [_observed("a"), _observed("b", data_bytes=10)], pick=False, cooling_down=True, selection=selection
    )

    reasons = {_values([c])[0]: c.hold_reason for c in pick.saved}
    assert reasons == {"a": HoldReason.COOLDOWN, "b": HoldReason.TOO_SMALL}


def test_a_not_due_hold_is_lifted_once_compaction_is_due():
    """A candidate held because compaction was not due is pending again at the next due plan."""
    first = _pick([], [_observed("a")], pick=False)
    pick = _pick(list(first.saved), [_observed("a")], now=NOW + timedelta(minutes=1))

    assert [c.state for c in pick.saved] == [CandidateState.PENDING]
    assert pick.shortfall is CandidateShortfall.AWAITING_SCHEDULE


def test_not_due_keeps_a_live_grant():
    """A grant made before compaction stopped being due stays until its lease ends."""
    observed = [_observed("a")]
    pick = _pick(_granted(observed, {"a"}), observed, pick=False)

    assert [c.state for c in pick.saved] == [CandidateState.GRANTED]


def test_candidates_take_the_policy_priority():
    """Every candidate carries the priority of the policy that applies now."""
    first = _pick([], [_observed("a")], pick=False)
    pick = _pick(list(first.saved), [_observed("a"), _observed("b")], priority=MaintenancePriority.P0)

    assert {c.priority for c in pick.saved} == {MaintenancePriority.P0}


def test_a_retried_pick_returns_the_runs_own_claims():
    """Picking again for the run that already claimed returns those claims, not new ones."""
    observed = [_observed("a", 6), _observed("b", 9), _observed("c", 8)]
    first = _pick(_granted(observed, {"b", "c"}), observed)
    again = _pick(list(first.saved), [_observed("a", 20), _observed("b", 9), _observed("c", 8)])

    assert _values(again.selected) == ["b", "c"]
    assert [c.state for c in again.saved if _values([c]) == ["a"]] == [CandidateState.PENDING]


def test_all_held_says_when_the_first_hold_ends():
    """When every qualifying candidate is held, nothing is picked and the shortfall says when to look again."""
    pick = _pick([], [_observed("a", written=NOW - timedelta(seconds=30))])

    assert pick.selected == ()
    assert pick.shortfall is CandidateShortfall.ALL_HELD
    assert pick.next_eligible_at == NOW + timedelta(seconds=90)


def test_all_claimed_says_when_the_first_lease_ends():
    """When another run holds every candidate, nothing is picked until its lease ends."""
    observed = [_observed("a")]
    first = _pick(_granted(observed, {"a"}), observed, claim_for=OTHER)

    pick = _pick(list(first.saved), observed, now=NOW + timedelta(minutes=1))

    assert pick.selected == ()
    assert pick.shortfall is CandidateShortfall.ALL_CLAIMED
    assert pick.next_eligible_at == LEASE


def test_claims_of_finished_runs_are_released_to_the_next_round():
    """A claim of a run that has finished is handed back as pending, for the next round to grant."""
    observed = [_observed("a")]
    first = _pick(_granted(observed, {"a"}), observed, claim_for=OTHER)

    pick = _pick(list(first.saved), observed, released_runs=frozenset({OTHER}))

    assert pick.selected == ()
    assert pick.shortfall is CandidateShortfall.AWAITING_SCHEDULE
    assert [(c.state, c.claimed_by_run_id) for c in pick.saved] == [(CandidateState.PENDING, None)]


def test_dropped_partitions_are_removed():
    """A candidate whose partition no longer qualifies is removed."""
    first = _pick([], [_observed("a"), _observed("b")], pick=False)

    pick = _pick(list(first.saved), [_observed("b")], pick=False)

    assert len(pick.removed) == 1
    assert _values(pick.saved) == ["b"]
