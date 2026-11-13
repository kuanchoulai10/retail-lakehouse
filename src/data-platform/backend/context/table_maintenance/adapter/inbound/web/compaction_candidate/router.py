"""Define the compaction candidate router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends

from context.table_maintenance.adapter.inbound.web.compaction_candidate.dto import (
    CandidatePartitionApiResponse,
    CompactionCandidateApiResponse,
    CompactionCandidatesApiResponse,
)
from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.application.port.inbound.compaction_candidate import (
    ListCompactionCandidatesUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.compaction_candidate import (
        ListCompactionCandidatesUseCaseOutputItem,
    )

router = APIRouter(tags=["compaction-candidates"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("/tables/{table_uuid}/compaction-candidates")
def list_compaction_candidates(table_uuid: str, use_cases: UseCases) -> CompactionCandidatesApiResponse:
    """List the table's compaction candidates, best first, and how many partitions one run compacts."""
    output = use_cases.list_compaction_candidates.execute(ListCompactionCandidatesUseCaseInput(table_uuid=table_uuid))
    return CompactionCandidatesApiResponse(
        partitions_per_run=output.partitions_per_run,
        candidates=[_candidate(item) for item in output.items],
    )


def _candidate(item: ListCompactionCandidatesUseCaseOutputItem) -> CompactionCandidateApiResponse:
    return CompactionCandidateApiResponse(
        partition=CandidatePartitionApiResponse(spec_id=item.spec_id, values=item.values),
        partition_label=item.partition_label,
        state=item.state,
        hold_reason=item.hold_reason,
        reducible_files=item.reducible_files,
        data_bytes=item.data_bytes,
        estimated_gb_hours=item.estimated_gb_hours,
        score=item.score,
        rank=item.rank,
        claimed_by_run_id=item.claimed_by_run_id,
        lease_expires_at=item.lease_expires_at,
        last_written_at=item.last_written_at,
        observed_at=item.observed_at,
    )
