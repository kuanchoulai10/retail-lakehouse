"""Test the ReleaseCompactionCandidatesService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from context.table_maintenance.application.domain.model.compaction_candidate import (
    CandidateScore,
    CandidateState,
    CompactionCandidate,
    PartitionKey,
)
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ReleaseCompactionCandidatesUseCaseInput,
)
from context.table_maintenance.application.service.compaction_candidate import ReleaseCompactionCandidatesService
from tests.context.table_maintenance.fakes.in_memory_compaction_candidates_repo import (
    InMemoryCompactionCandidatesRepo,
)

NOW = datetime(2026, 11, 13, 12, tzinfo=UTC)
RUN = TableMaintenanceRunId("run-1")


def _candidate(value: str, run: TableMaintenanceRunId | None) -> CompactionCandidate:
    candidate = CompactionCandidate.create(
        table_uuid=TableId("t-1"),
        partition=PartitionKey(spec_id=0, values=(value,)),
        label=value,
        score=CandidateScore(reducible_files=5, data_bytes=1, estimated_gb_hours=0.0, score=0.5),
        last_written_at=None,
        hold_reason=None,
        now=NOW,
    )
    if run is not None:
        candidate.grant("round-1", NOW + timedelta(minutes=10), NOW)
        candidate.claim(run, NOW + timedelta(hours=1), NOW)
    return candidate


def test_release_hands_back_every_candidate_the_run_holds():
    """The run's candidates are pending again; another run's and free ones are untouched."""
    repo = InMemoryCompactionCandidatesRepo()
    repo.save_all(
        [_candidate("a", RUN), _candidate("b", RUN), _candidate("c", TableMaintenanceRunId("x")), _candidate("d", None)]
    )

    output = ReleaseCompactionCandidatesService(repo).execute(
        ReleaseCompactionCandidatesUseCaseInput(run_id="run-1", now=NOW + timedelta(minutes=1))
    )

    assert output.released == 2
    states = {c.partition.values[0]: c.state for c in repo.list_all()}
    assert states == {
        "a": CandidateState.PENDING,
        "b": CandidateState.PENDING,
        "c": CandidateState.CLAIMED,
        "d": CandidateState.PENDING,
    }


def test_release_twice_changes_nothing_more():
    """A retried release finds nothing more to hand back."""
    repo = InMemoryCompactionCandidatesRepo()
    repo.save_all([_candidate("a", RUN)])
    service = ReleaseCompactionCandidatesService(repo)
    request = ReleaseCompactionCandidatesUseCaseInput(run_id="run-1", now=NOW)

    service.execute(request)
    assert service.execute(request).released == 0
