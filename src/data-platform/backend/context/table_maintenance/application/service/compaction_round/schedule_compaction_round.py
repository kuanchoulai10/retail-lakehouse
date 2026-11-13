"""Define the ScheduleCompactionRoundService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_round import CompactionRoundId
from context.table_maintenance.application.domain.service.compaction_round import plan_compaction_round
from context.table_maintenance.application.port.inbound.compaction_round import (
    ScheduleCompactionRoundUseCase,
    ScheduleCompactionRoundUseCaseInput,
    ScheduleCompactionRoundUseCaseOutput,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import timedelta

    from context.table_maintenance.application.domain.model.compaction_round import (
        CompactionRound,
        PriorityWeights,
    )
    from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
    from context.table_maintenance.application.port.outbound.compaction_candidate import CompactionCandidatesRepo
    from context.table_maintenance.application.port.outbound.compaction_round import CompactionRoundsRepo


class ScheduleCompactionRoundService(ScheduleCompactionRoundUseCase):
    """Run one round of the compaction scheduler across every table.

    It ranks every pending candidate, grants the picks to their tables for
    ``grant_lease`` (the tables' reconciliations claim them for runs), records
    the round and keeps only the newest ``rounds_kept`` rounds.
    """

    def __init__(  # noqa: PLR0913
        self,
        candidates_repo: CompactionCandidatesRepo,
        rounds_repo: CompactionRoundsRepo,
        *,
        weights: PriorityWeights,
        budget_gb_hours: float,
        partitions_per_run: int,
        sla: Mapping[MaintenancePriority, timedelta],
        grant_lease: timedelta,
        rounds_kept: int,
        skipped_kept: int = 20,
    ) -> None:
        """Bind the repos and the round's rules: weights, budget, per-table share, SLA, lease and retention."""
        self._candidates_repo = candidates_repo
        self._rounds_repo = rounds_repo
        self._weights = weights
        self._budget_gb_hours = budget_gb_hours
        self._partitions_per_run = partitions_per_run
        self._sla = dict(sla)
        self._grant_lease = grant_lease
        self._rounds_kept = rounds_kept
        self._skipped_kept = skipped_kept

    def execute(self, request: ScheduleCompactionRoundUseCaseInput) -> ScheduleCompactionRoundUseCaseOutput:
        """Plan the round, grant its picks in one save, then record it and purge old rounds.

        A round already recorded under ``round_id`` (a retry after it saved) is
        answered as recorded and grants nothing more. The grants are saved before
        the round, all or none: when a candidate changed since it was read,
        ``StaleCompactionCandidate`` propagates with nothing stored, and the
        caller runs the round again.
        """
        round_id = CompactionRoundId(request.round_id)
        recorded = self._rounds_repo.get(round_id)
        if recorded is not None:
            return _output(recorded)
        pending = self._candidates_repo.list_pending()
        round_ = plan_compaction_round(
            pending,
            round_id=round_id,
            weights=self._weights,
            budget_gb_hours=self._budget_gb_hours,
            partitions_per_run=self._partitions_per_run,
            sla=self._sla,
            now=request.now,
            skipped_kept=self._skipped_kept,
        )
        picked = {(p.table_uuid, p.partition.canonical()) for p in round_.picks}
        granted = [c for c in pending if (c.table_uuid, c.partition.canonical()) in picked]
        for candidate in granted:
            candidate.grant(round_id.value, request.now + self._grant_lease, request.now)
        self._candidates_repo.save_all(granted)
        self._rounds_repo.save(round_)
        self._rounds_repo.purge(keep=self._rounds_kept)
        return _output(round_)


def _output(round_: CompactionRound) -> ScheduleCompactionRoundUseCaseOutput:
    return ScheduleCompactionRoundUseCaseOutput(
        round_id=round_.id.value,
        granted_table_uuids=[t.value for t in round_.granted_tables()],
        picked=len(round_.picks),
        skipped_total=round_.skipped_total,
        used_gb_hours=round_.used_gb_hours,
        budget_gb_hours=round_.budget_gb_hours,
    )
