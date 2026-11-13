"""Define the ListCompactionCandidatesService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import CandidateState
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ListCompactionCandidatesUseCase,
    ListCompactionCandidatesUseCaseInput,
    ListCompactionCandidatesUseCaseOutput,
    ListCompactionCandidatesUseCaseOutputItem,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import timedelta

    from context.table_maintenance.application.domain.model.compaction_candidate import CompactionCandidate
    from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
    from context.table_maintenance.application.port.outbound.compaction_candidate import CompactionCandidatesRepo
    from context.table_maintenance.application.port.outbound.table import TablesRepo


class ListCompactionCandidatesService(ListCompactionCandidatesUseCase):
    """List a table's compaction candidates, best first, with the rank of each pending one.

    Each candidate is marked overdue when it has waited for a run longer than
    ``sla`` gives its priority, as of ``clock``.
    """

    def __init__(
        self,
        candidates_repo: CompactionCandidatesRepo,
        tables_repo: TablesRepo,
        *,
        partitions_per_run: int,
        sla: Mapping[MaintenancePriority, timedelta],
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Bind the repos, how many candidates one run takes, the SLA per priority and the clock."""
        self._candidates_repo = candidates_repo
        self._tables_repo = tables_repo
        self._partitions_per_run = partitions_per_run
        self._sla = dict(sla)
        self._clock = clock

    def execute(self, request: ListCompactionCandidatesUseCaseInput) -> ListCompactionCandidatesUseCaseOutput:
        """Return the table's candidates sorted as a run picks them; a table maintenance does not know is not found."""
        table_uuid = TableId(request.table_uuid)
        if self._tables_repo.get(table_uuid) is None:
            raise NotFoundError(f"table {request.table_uuid} not found")
        ranked = sorted(self._candidates_repo.list_by_table(table_uuid), key=lambda c: c.rank)
        pending = [c.id for c in ranked if c.state is CandidateState.PENDING]
        ranks = {candidate_id: place for place, candidate_id in enumerate(pending, start=1)}
        now = self._clock()
        return ListCompactionCandidatesUseCaseOutput(
            partitions_per_run=self._partitions_per_run,
            items=[_item(c, ranks.get(c.id), overdue=c.overdue(self._sla, now)) for c in ranked],
        )


def _item(
    candidate: CompactionCandidate, rank: int | None, *, overdue: bool
) -> ListCompactionCandidatesUseCaseOutputItem:
    return ListCompactionCandidatesUseCaseOutputItem(
        spec_id=candidate.partition.spec_id,
        values=list(candidate.partition.values),
        partition_label=candidate.label,
        state=candidate.state.value,
        hold_reason=None if candidate.hold_reason is None else candidate.hold_reason.value,
        reducible_files=candidate.score.reducible_files,
        data_bytes=candidate.score.data_bytes,
        estimated_gb_hours=candidate.score.estimated_gb_hours,
        score=candidate.score.score,
        rank=rank,
        claimed_by_run_id=None if candidate.claimed_by_run_id is None else candidate.claimed_by_run_id.value,
        lease_expires_at=candidate.lease_expires_at,
        last_written_at=candidate.last_written_at,
        observed_at=candidate.observed_at,
        priority=candidate.priority.value,
        granted_round_id=candidate.granted_round_id,
        pending_since=candidate.pending_since,
        overdue=overdue,
    )
