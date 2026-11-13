"""Tests for the select_top_candidates domain service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CompactionCandidate,
    HoldReason,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.domain.service.compaction_candidate import select_top_candidates

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)


def _candidate(value: str, score: float, reducible: int = 10, hold: HoldReason | None = None) -> CompactionCandidate:
    return CompactionCandidate.create(
        table_uuid=TableId("t-1"),
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=value,
        score=CandidateScore(reducible_files=reducible, data_bytes=1, estimated_gb_hours=0.0, score=score),
        last_written_at=None,
        hold_reason=hold,
        now=NOW,
    )


def _values(selected) -> list[str]:  # noqa: ANN001
    return [c.partition.values[0] for c in selected]


def test_takes_the_highest_scores_first():
    """The best N pending candidates are taken, best first."""
    candidates = [_candidate("a", 0.2), _candidate("b", 0.9), _candidate("c", 0.5), _candidate("d", 0.7)]
    assert _values(select_top_candidates(candidates, 2)) == ["b", "d"]


def test_takes_only_pending_candidates():
    """Held and claimed candidates are not taken."""
    claimed = _candidate("claimed", 0.99)
    claimed.claim(TableMaintenanceRunId("r"), NOW + timedelta(hours=1), NOW)
    candidates = [_candidate("held", 0.95, hold=HoldReason.TOO_SMALL), claimed, _candidate("free", 0.1)]
    assert _values(select_top_candidates(candidates, 5)) == ["free"]


def test_ties_go_to_more_removable_files_then_to_the_partition_key():
    """Equal scores are ordered by removable files, then by the partition, so the choice is stable."""
    candidates = [
        _candidate("z", 0.5, reducible=3),
        _candidate("b", 0.5, reducible=3),
        _candidate("y", 0.5, reducible=9),
    ]
    assert _values(select_top_candidates(candidates, 3)) == ["y", "b", "z"]


def test_nothing_is_taken_for_zero():
    """Taking zero takes nothing."""
    assert select_top_candidates([_candidate("a", 0.5)], 0) == ()
