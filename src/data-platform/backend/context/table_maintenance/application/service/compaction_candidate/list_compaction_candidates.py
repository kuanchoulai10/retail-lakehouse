"""Define the ListCompactionCandidatesService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import CandidateState
from context.table_maintenance.application.domain.model.compaction_round import CompactionRoundId
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ListCompactionCandidatesUseCase,
    ListCompactionCandidatesUseCaseInput,
    ListCompactionCandidatesUseCaseOutput,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import timedelta

    from context.table_maintenance.application.domain.model.compaction_candidate import CompactionCandidate
    from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
    from context.table_maintenance.application.port.outbound.compaction_candidate import CompactionCandidatesRepo
    from context.table_maintenance.application.port.outbound.compaction_round import CompactionRoundsRepo
    from context.table_maintenance.application.port.outbound.table import TablesRepo


class ListCompactionCandidatesService(ListCompactionCandidatesUseCase):
    """List a table's compaction candidates, best first, with the rank of each pending one.

    Each candidate is marked overdue when it has waited for a run longer than
    ``sla`` gives its priority, as of ``clock``. A grant whose lease ended
    unclaimed is listed as the pending candidate the next observation makes
    it: ranked, without its round or lease. A grant also says when its round
    started, which is how the rounds list names the round.
    """

    def __init__(
        self,
        candidates_repo: CompactionCandidatesRepo,
        tables_repo: TablesRepo,
        rounds_repo: CompactionRoundsRepo,
        *,
        partitions_per_run: int,
        sla: Mapping[MaintenancePriority, timedelta],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, how many candidates one run takes, the SLA per priority and the clock."""
        self._candidates_repo = candidates_repo
        self._tables_repo = tables_repo
        self._rounds_repo = rounds_repo
        self._partitions_per_run = partitions_per_run
        self._sla = dict(sla)
        self._clock = clock

    def execute(self, request: ListCompactionCandidatesUseCaseInput) -> ListCompactionCandidatesUseCaseOutput:
        """Return the table's candidates sorted as a run picks them; a table maintenance does not know is not found."""
        table_uuid = TableId(request.table_uuid)
        if self._tables_repo.get(table_uuid) is None:
            raise NotFoundError(f"table {request.table_uuid} not found")
        ranked = sorted(self._candidates_repo.list_by_table(table_uuid), key=lambda c: c.rank)
        now = self._clock()
        expired = {c.id for c in ranked if c.grant_expired(now)}
        pending = [c.id for c in ranked if c.state is CandidateState.PENDING or c.id in expired]
        ranks = {candidate_id: place for place, candidate_id in enumerate(pending, start=1)}
        started = self._round_starts({c.granted_round_id for c in ranked if c.granted_round_id and c.id not in expired})
        return ListCompactionCandidatesUseCaseOutput(
            partitions_per_run=self._partitions_per_run,
            items=tuple(
                _item(
                    c,
                    ranks.get(c.id),
                    overdue=c.overdue(self._sla, now),
                    expired=c.id in expired,
                    round_started_at=None if c.granted_round_id is None else started.get(c.granted_round_id),
                )
                for c in ranked
            ),
        )

    def _round_starts(self, round_ids: set[str]) -> dict[str, datetime]:
        """Return when each of these rounds started; a round no longer kept is left out."""
        starts: dict[str, datetime] = {}
        for round_id in sorted(round_ids):
            round_ = self._rounds_repo.get(CompactionRoundId(round_id))
            if round_ is not None:
                starts[round_id] = round_.started_at
        return starts


def _item(
    candidate: CompactionCandidate,
    rank: int | None,
    *,
    overdue: bool,
    expired: bool,
    round_started_at: datetime | None,
) -> ListCompactionCandidatesUseCaseOutput.CompactionCandidate:
    return ListCompactionCandidatesUseCaseOutput.CompactionCandidate(
        spec_id=candidate.partition.spec_id,
        values=tuple(candidate.partition.values),
        partition_label=candidate.label,
        state=CandidateState.PENDING.value if expired else candidate.state.value,
        hold_reason=None if candidate.hold_reason is None else candidate.hold_reason.value,
        reducible_files=candidate.score.reducible_files,
        data_bytes=candidate.score.data_bytes,
        estimated_gb_hours=candidate.score.estimated_gb_hours,
        score=candidate.score.score,
        rank=rank,
        claimed_by_run_id=None if candidate.claimed_by_run_id is None else candidate.claimed_by_run_id.value,
        lease_expires_at=None if expired else candidate.lease_expires_at,
        last_written_at=candidate.last_written_at,
        observed_at=candidate.observed_at,
        priority=candidate.priority.value,
        granted_round_id=None if expired else candidate.granted_round_id,
        pending_since=candidate.pending_since,
        overdue=overdue,
        granted_round_started_at=None if expired else round_started_at,
    )
