"""Define the plan_service_on_fakes helper."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import CandidateSelection
from context.table_maintenance.application.domain.model.shared import ComputeSize, SizeMemory
from context.table_maintenance.application.service.table import PlanTableMaintenanceService
from tests.context.table_maintenance.fakes.in_memory_compaction_candidates_repo import (
    InMemoryCompactionCandidatesRepo,
)
from tests.context.table_maintenance.fakes.in_memory_table_maintenance_runs_repo import (
    InMemoryTableMaintenanceRunsRepo,
)
from tests.context.table_maintenance.fakes.plan_after_a_round import PlanAfterARound

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table import PlanTableMaintenanceUseCase
    from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment import (
        ResolveApplicableTableMaintenancePolicyUseCase,
    )
    from context.table_maintenance.application.port.outbound.compaction_candidate import CompactionCandidatesRepo
    from context.table_maintenance.application.port.outbound.table import ReadTableMetadataGateway, TablesRepo
    from context.table_maintenance.application.port.outbound.table_maintenance_run import TableMaintenanceRunsRepo

MIB = 1024**2
GIB = 1024**3
SIZE_MEMORY = {
    ComputeSize.S: SizeMemory(driver_bytes=768 * MIB, executor_bytes=768 * MIB),
    ComputeSize.M: SizeMemory(driver_bytes=GIB, executor_bytes=1536 * MIB),
    ComputeSize.L: SizeMemory(driver_bytes=1536 * MIB, executor_bytes=2 * GIB),
}
CLAIM_LEASE = timedelta(hours=19)


def plan_service_on_fakes(  # noqa: PLR0913
    tables_repo: TablesRepo,
    catalog: ReadTableMetadataGateway,
    resolve_applicable_policy: ResolveApplicableTableMaintenancePolicyUseCase,
    candidates_repo: CompactionCandidatesRepo | None = None,
    runs_repo: TableMaintenanceRunsRepo | None = None,
    selection: CandidateSelection | None = None,
) -> PlanTableMaintenanceUseCase:
    """Return the plan service on the given fakes, with empty candidate and run repos unless given.

    A compaction round grants every pending candidate before each scheduled plan
    (``PlanAfterARound``), so a due compaction is planned at once.
    """
    candidates = InMemoryCompactionCandidatesRepo() if candidates_repo is None else candidates_repo
    service = PlanTableMaintenanceService(
        tables_repo,
        catalog,
        resolve_applicable_policy,
        candidates,
        InMemoryTableMaintenanceRunsRepo() if runs_repo is None else runs_repo,
        selection=CandidateSelection() if selection is None else selection,
        size_memory=SIZE_MEMORY,
        claim_lease=CLAIM_LEASE,
    )
    return PlanAfterARound(service, candidates)
