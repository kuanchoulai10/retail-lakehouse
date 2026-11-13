"""Define the PlanAfterARound test double."""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.table import PlanTableMaintenanceUseCase
from context.table_maintenance.application.port.outbound.compaction_candidate import CandidateState

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import (
        PlanTableMaintenanceUseCaseInput,
        PlanTableMaintenanceUseCaseOutput,
    )
    from context.table_maintenance.application.port.outbound.compaction_candidate import CompactionCandidatesRepo

GRANT_LEASE = timedelta(minutes=10)


class PlanAfterARound(PlanTableMaintenanceUseCase):
    """Plan a table as if a compaction round had granted every pending candidate just before.

    A scheduled plan first syncs the candidates (a plan for no run), then every
    pending candidate is granted, then the plan asked for runs. Tests of what a
    plan renders use it so a due compaction is planned at once, as it was before
    compaction rounds existed; a manual plan is passed straight through.
    """

    def __init__(self, planner: PlanTableMaintenanceUseCase, candidates_repo: CompactionCandidatesRepo) -> None:
        """Wrap the plan service and the candidates repo it writes."""
        self._planner = planner
        self._candidates_repo = candidates_repo

    def execute(self, request: PlanTableMaintenanceUseCaseInput) -> PlanTableMaintenanceUseCaseOutput:
        """Sync, grant every pending candidate, then plan."""
        if request.manual_operations is None:
            self._planner.execute(replace(request, run_id=None))
            pending = [c for c in self._candidates_repo.list_unheld() if c.state is CandidateState.PENDING]
            for candidate in pending:
                candidate.grant("round-before-plan", request.now + GRANT_LEASE, request.now)
            self._candidates_repo.save_all(pending)
        return self._planner.execute(request)
