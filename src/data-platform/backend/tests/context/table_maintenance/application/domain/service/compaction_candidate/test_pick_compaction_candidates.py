"""Tests for the pick_compaction_candidates domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateFilters,
    CandidateSelection,
    CandidateShortfall,
    CandidateState,
    ObservedPartition,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.domain.service.compaction_candidate import (
    pick_compaction_candidates,
)

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
TABLE = TableId("t-1")
RUN = TableMaintenanceRunId("run-1")
OTHER = TableMaintenanceRunId("run-2")
LEASE = NOW + timedelta(hours=2)
SELECTION = CandidateSelection(partitions_per_run=2, filters=CandidateFilters(quiet_seconds=120))


def _observed(value: str, reducible: int = 10, written: datetime | None = None) -> ObservedPartition:
    return ObservedPartition(
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"region={value}",
        reducible_files=reducible,
        data_bytes=1000,
        last_written_at=written,
    )


def _pick(existing, observed, **overrides: Any):  # noqa: ANN001, ANN202
    arguments: dict[str, Any] = {
        "selection": SELECTION,
        "memory_gb": 1.5,
        "throughput_bytes_per_hour": 1e9,
        "released_runs": frozenset(),
        "pick": True,
        "claim_for": RUN,
        "lease_until": LEASE,
        "now": NOW,
    }
    arguments.update(overrides)
    return pick_compaction_candidates(TABLE, existing, observed, **arguments)


def _values(candidates) -> list[str]:  # noqa: ANN001
    return [str(c.partition.values[0]) for c in candidates]


def test_picks_and_claims_the_best_pending_candidates():
    """The two best pending candidates are picked, best first, and claimed for the run."""
    pick = _pick([], [_observed("a", 6), _observed("b", 9), _observed("c", 8)])

    assert _values(pick.selected) == ["b", "c"]
    assert {c.state for c in pick.selected} == {CandidateState.CLAIMED}
    assert {c.claimed_by_run_id for c in pick.selected} == {RUN}
    assert pick.shortfall is None
    assert sorted(_values(pick.saved)) == ["a", "b", "c"]


def test_picks_without_claiming_when_no_run_is_named():
    """Without a run to claim for, the best candidates are picked but stay pending."""
    pick = _pick([], [_observed("a", 6), _observed("b", 9)], claim_for=None)

    assert _values(pick.selected) == ["b", "a"]
    assert {c.state for c in pick.saved} == {CandidateState.PENDING}


def test_picks_nothing_when_compaction_is_not_due():
    """Candidates are still synced when compaction is not due, but none is picked."""
    pick = _pick([], [_observed("a")], pick=False)

    assert pick.selected == ()
    assert pick.shortfall is None
    assert [c.state for c in pick.saved] == [CandidateState.PENDING]


def test_a_retried_pick_returns_the_runs_own_claims():
    """Picking again for the run that already claimed returns those claims, not new ones."""
    first = _pick([], [_observed("a", 6), _observed("b", 9), _observed("c", 8)])
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
    first = _pick([], [_observed("a")], claim_for=OTHER)

    pick = _pick(list(first.saved), [_observed("a")], now=NOW + timedelta(minutes=1))

    assert pick.selected == ()
    assert pick.shortfall is CandidateShortfall.ALL_CLAIMED
    assert pick.next_eligible_at == LEASE


def test_claims_of_finished_runs_are_released_first():
    """A claim of a run that has finished is handed back and can be picked again."""
    first = _pick([], [_observed("a")], claim_for=OTHER)

    pick = _pick(list(first.saved), [_observed("a")], released_runs=frozenset({OTHER}))

    assert [c.claimed_by_run_id for c in pick.selected] == [RUN]


def test_dropped_partitions_are_removed():
    """A candidate whose partition no longer qualifies is removed."""
    first = _pick([], [_observed("a"), _observed("b")], pick=False)

    pick = _pick(list(first.saved), [_observed("b")], pick=False)

    assert len(pick.removed) == 1
    assert _values(pick.saved) == ["b"]
