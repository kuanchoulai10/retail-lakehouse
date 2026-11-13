"""Define the ReleaseCompactionCandidatesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_run import TableMaintenanceRunId
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ReleaseCompactionCandidatesUseCase,
    ReleaseCompactionCandidatesUseCaseInput,
    ReleaseCompactionCandidatesUseCaseOutput,
)
from context.table_maintenance.application.service.shared import translate_domain_errors

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.compaction_candidate import (
        CompactionCandidatesRepo,
    )


class ReleaseCompactionCandidatesService(ReleaseCompactionCandidatesUseCase):
    """Hand back the candidates a run claimed when the run never started, so the next plan can pick them."""

    def __init__(self, candidates_repo: CompactionCandidatesRepo) -> None:
        """Bind the candidates repo."""
        self._candidates_repo = candidates_repo

    def execute(self, request: ReleaseCompactionCandidatesUseCaseInput) -> ReleaseCompactionCandidatesUseCaseOutput:
        """Turn every candidate the run holds pending again; ones its run finished are left as they are."""
        with translate_domain_errors():
            run_id = TableMaintenanceRunId(request.run_id)
            held = [c for c in self._candidates_repo.list_by_run(run_id) if c.state.holds_a_claim]
            for candidate in held:
                candidate.release(run_id, request.now)
            self._candidates_repo.save_all(held)
        return ReleaseCompactionCandidatesUseCaseOutput(released=len(held))
