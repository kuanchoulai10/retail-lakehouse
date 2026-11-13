"""Tests for the plan_compaction_round domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CompactionCandidate,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.compaction_round import (
    CompactionRoundId,
    PriorityWeights,
    SkipReason,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.domain.service.compaction_round import plan_compaction_round

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
ROUND = CompactionRoundId("round-1")
WEIGHTS = PriorityWeights(p0=4.0, p1=2.0, p2=1.0)
SLA = {
    MaintenancePriority.P0: timedelta(hours=1),
    MaintenancePriority.P1: timedelta(hours=4),
    MaintenancePriority.P2: timedelta(hours=8),
}


def _candidate(  # noqa: PLR0913
    table: str,
    value: str,
    *,
    score: float = 0.5,
    gb_hours: float = 0.01,
    priority: MaintenancePriority = MaintenancePriority.P2,
    pending_since: datetime = NOW,
) -> CompactionCandidate:
    return CompactionCandidate.create(
        table_uuid=TableId(table),
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=f"day={value}",
        score=CandidateScore(reducible_files=5, data_bytes=1000, estimated_gb_hours=gb_hours, score=score),
        last_written_at=None,
        hold_reason=None,
        now=pending_since,
        priority=priority,
    )


def _plan(candidates, *, budget: float = 0.05, per_run: int = 10, kept: int = 20):  # noqa: ANN001, ANN202
    return plan_compaction_round(
        candidates,
        round_id=ROUND,
        weights=WEIGHTS,
        budget_gb_hours=budget,
        partitions_per_run=per_run,
        sla=SLA,
        now=NOW,
        skipped_kept=kept,
    )


def _picked(round_) -> list[str]:  # noqa: ANN001
    return [f"{p.table_uuid.value}/{p.partition.values[0]}" for p in round_.picks]


def test_ranks_by_score_times_priority_weight():
    """A P0 candidate scored 0.3 (weighted 1.2) goes before a P2 one scored 0.9."""
    round_ = _plan(
        [_candidate("t-2", "low", score=0.9), _candidate("t-1", "urgent", score=0.3, priority=MaintenancePriority.P0)]
    )

    assert _picked(round_) == ["t-1/urgent", "t-2/low"]
    first = round_.picks[0]
    assert (first.priority, first.score, first.weighted_score) == (MaintenancePriority.P0, 0.3, pytest.approx(1.2))


def test_stops_at_the_first_candidate_over_the_budget():
    """Two 0.02 fit 0.05, the third does not; it and everything after it, even smaller, are skipped budget used."""
    round_ = _plan(
        [
            _candidate("t-1", "a", score=0.9, gb_hours=0.02),
            _candidate("t-1", "b", score=0.8, gb_hours=0.02),
            _candidate("t-2", "c", score=0.7, gb_hours=0.02),
            _candidate("t-2", "d", score=0.6, gb_hours=0.001),
        ]
    )

    assert _picked(round_) == ["t-1/a", "t-1/b"]
    assert [(s.partition.values[0], s.reason) for s in round_.skips] == [
        ("c", SkipReason.BUDGET_USED),
        ("d", SkipReason.BUDGET_USED),
    ]
    assert round_.used_gb_hours == pytest.approx(0.04)
    assert round_.budget_gb_hours == 0.05


def test_always_takes_the_first_candidate():
    """A candidate larger than the whole budget is still taken when it comes first, so it is never starved."""
    round_ = _plan([_candidate("t-1", "huge", gb_hours=0.2), _candidate("t-2", "small", score=0.1)])

    assert _picked(round_) == ["t-1/huge"]
    assert round_.used_gb_hours == pytest.approx(0.2)
    assert [s.reason for s in round_.skips] == [SkipReason.BUDGET_USED]


def test_caps_each_table_at_partitions_per_run():
    """A table's third candidate is skipped as its share is used, and the walk goes on to other tables."""
    round_ = _plan(
        [
            _candidate("t-1", "a", score=0.9),
            _candidate("t-1", "b", score=0.8),
            _candidate("t-1", "c", score=0.7),
            _candidate("t-2", "d", score=0.6),
        ],
        per_run=2,
    )

    assert _picked(round_) == ["t-1/a", "t-1/b", "t-2/d"]
    assert [(s.partition.values[0], s.reason) for s in round_.skips] == [("c", SkipReason.TABLE_SHARE_USED)]


def test_keeps_the_first_skipped_and_counts_all():
    """Only the first skipped are kept on the round; the count covers all of them."""
    candidates = [_candidate("t-1", "first", score=0.99, gb_hours=0.05)] + [
        _candidate("t-2", str(i), score=0.5 - i / 100) for i in range(5)
    ]

    round_ = _plan(candidates, kept=2)

    assert [s.partition.values[0] for s in round_.skips] == ["0", "1"]
    assert round_.skipped_total == 5


def test_marks_overdue_candidates():
    """A pick or skip that waited longer than its priority's SLA says so."""
    round_ = _plan(
        [
            _candidate("t-1", "old", score=0.9, gb_hours=0.04, pending_since=NOW - timedelta(hours=9)),
            _candidate("t-2", "new", score=0.8, pending_since=NOW - timedelta(hours=1)),
            _candidate(
                "t-3", "late", score=0.7, priority=MaintenancePriority.P0, pending_since=NOW - timedelta(hours=2)
            ),
        ]
    )

    assert [(p.label, p.overdue) for p in round_.picks] == [("day=late", True), ("day=old", True)]
    assert [(s.label, s.overdue) for s in round_.skips] == [("day=new", False)]


def test_ties_go_to_the_candidate_rank():
    """Equal weighted scores fall back to the candidate rank: more removable files, then the partition key."""
    a = _candidate("t-1", "b")
    b = _candidate("t-1", "a")

    assert _picked(_plan([a, b])) == ["t-1/a", "t-1/b"]


def test_empty_round():
    """With no pending candidate the round picks nothing, skips nothing and uses nothing."""
    round_ = _plan([])

    assert (round_.picks, round_.skips, round_.skipped_total, round_.used_gb_hours) == ((), (), 0, 0.0)
    assert round_.granted_tables() == ()
    assert round_.id == ROUND
    assert round_.started_at == NOW


def test_granted_tables_are_unique_in_pick_order():
    """Each table that got a pick is named once, in the order of its first pick."""
    round_ = _plan(
        [
            _candidate("t-2", "a", score=0.9),
            _candidate("t-1", "b", score=0.8),
            _candidate("t-2", "c", score=0.7),
        ]
    )

    assert [t.value for t in round_.granted_tables()] == ["t-2", "t-1"]


def _busy(table: str, value: str, state: str) -> CompactionCandidate:
    """A candidate of ``table`` that a round granted (``granted``), a run holds (``running``) or finished (``done``)."""
    candidate = _candidate(table, value, score=0.99)
    candidate.grant("round-0", NOW + timedelta(minutes=10), NOW - timedelta(minutes=1))
    if state != "granted":
        run = TableMaintenanceRunId("run-1")
        candidate.claim(run, NOW + timedelta(hours=1), NOW - timedelta(minutes=1))
        candidate.start(run, NOW - timedelta(minutes=1))
        if state == "done":
            candidate.finish(run, succeeded=True, now=NOW - timedelta(seconds=10))
    return candidate


@pytest.mark.parametrize("state", ["granted", "running", "done"])
def test_a_busy_table_gets_nothing_and_an_idle_one_gets_the_budget(state):
    """A table with a live grant or run, or one not observed since its run ended, gets nothing, counted apart."""
    round_ = _plan(
        [
            _busy("t-busy", "taken", state),
            _candidate("t-busy", "more", score=0.9, gb_hours=0.02),
            _candidate("t-idle", "a", score=0.5, gb_hours=0.02),
            _candidate("t-idle", "b", score=0.4, gb_hours=0.02),
        ]
    )

    assert _picked(round_) == ["t-idle/a", "t-idle/b"]
    assert (round_.skips, round_.skipped_total, round_.busy_skipped) == ((), 0, 1)


def test_only_pending_candidates_are_picked_or_skipped():
    """Granted, running and finished candidates only mark their table busy; they are neither picks nor skips."""
    round_ = _plan([_busy("t-1", "a", "granted"), _busy("t-2", "b", "running")])

    assert round_.picks == ()
    assert round_.skips == ()


def test_an_expired_grant_does_not_keep_its_table_busy():
    """A grant whose lease ended no longer holds the table."""
    stale = _candidate("t-1", "old")
    stale.grant("round-0", NOW - timedelta(seconds=1), NOW - timedelta(minutes=11))

    assert _picked(_plan([stale, _candidate("t-1", "new")])) == ["t-1/new"]


def test_a_table_over_its_share_reads_table_share_used_even_after_the_budget_ran_out():
    """The share is checked first: after the walk stopped, a full table's candidates still say why."""
    round_ = _plan(
        [
            _candidate("t-1", "a", score=0.9, gb_hours=0.04),
            _candidate("t-2", "big", score=0.8, gb_hours=0.04),
            _candidate("t-1", "b", score=0.7, gb_hours=0.001),
        ],
        per_run=1,
    )

    assert _picked(round_) == ["t-1/a"]
    assert [(s.partition.values[0], s.reason) for s in round_.skips] == [
        ("big", SkipReason.BUDGET_USED),
        ("b", SkipReason.TABLE_SHARE_USED),
    ]


def test_partitions_of_busy_tables_take_no_place_among_the_kept_skips():
    """A busy table's many partitions are only counted, so the budget's skips stay in view."""
    busy = [_candidate("t-busy", f"p{i}", priority=MaintenancePriority.P0, score=0.9) for i in range(25)]
    round_ = _plan(
        [
            _busy("t-busy", "taken", "running"),
            *busy,
            _candidate("t-1", "a", score=0.5, gb_hours=0.04),
            _candidate("t-2", "b", score=0.4, gb_hours=0.04),
        ],
        kept=20,
    )

    assert _picked(round_) == ["t-1/a"]
    assert [(s.table_uuid.value, s.reason) for s in round_.skips] == [("t-2", SkipReason.BUDGET_USED)]
    assert (round_.skipped_total, round_.busy_skipped) == (1, 25)
