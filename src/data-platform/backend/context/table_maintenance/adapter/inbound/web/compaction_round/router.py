"""Define the compaction round router."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 - FastAPI resolves the annotation at runtime
from typing import TYPE_CHECKING, Annotated, cast

from fastapi import APIRouter, Depends, Query

from context.table_maintenance.adapter.inbound.web.compaction_round.dto import (
    CompactionRoundApiResponse,
    CompactionRoundPartitionApiResponse,
    CompactionRoundPickApiResponse,
    CompactionRoundSkipApiResponse,
)
from context.table_maintenance.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.table_maintenance.application.port.inbound.compaction_round import (
    GetCompactionRoundUseCaseInput,
    ListCompactionRoundsUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.adapter.inbound.web.compaction_round.dto import (
        RoundPriorityApi,
        RoundSkipReasonApi,
    )
    from context.table_maintenance.application.port.inbound.compaction_round import (
        GetCompactionRoundUseCaseOutput,
        GetCompactionRoundUseCaseOutputPick,
        GetCompactionRoundUseCaseOutputSkip,
        ListCompactionRoundsUseCaseOutputItem,
        ListCompactionRoundsUseCaseOutputPick,
        ListCompactionRoundsUseCaseOutputSkip,
    )

    type _Round = ListCompactionRoundsUseCaseOutputItem | GetCompactionRoundUseCaseOutput
    type _Pick = ListCompactionRoundsUseCaseOutputPick | GetCompactionRoundUseCaseOutputPick
    type _Skip = ListCompactionRoundsUseCaseOutputSkip | GetCompactionRoundUseCaseOutputSkip

router = APIRouter(tags=["compaction-rounds"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("/compaction-rounds")
def list_compaction_rounds(
    use_cases: UseCases,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before: datetime | None = None,
) -> list[CompactionRoundApiResponse]:
    """List the recorded compaction rounds, newest first; ``before`` (a round's start) pages to older ones."""
    output = use_cases.list_compaction_rounds.execute(ListCompactionRoundsUseCaseInput(limit=limit, before=before))
    return [_round(item) for item in output.items]


@router.get("/compaction-rounds/{round_id}")
def get_compaction_round(round_id: str, use_cases: UseCases) -> CompactionRoundApiResponse:
    """Read one recorded compaction round."""
    return _round(use_cases.get_compaction_round.execute(GetCompactionRoundUseCaseInput(round_id=round_id)))


def _round(round_: _Round) -> CompactionRoundApiResponse:
    return CompactionRoundApiResponse(
        round_id=round_.round_id,
        started_at=round_.started_at,
        budget_gb_hours=round_.budget_gb_hours,
        used_gb_hours=round_.used_gb_hours,
        picks=[_pick(p) for p in round_.picks],
        skips=[_skip(s) for s in round_.skips],
        skipped_total=round_.skipped_total,
    )


def _pick(pick: _Pick) -> CompactionRoundPickApiResponse:
    return CompactionRoundPickApiResponse(
        table_uuid=pick.table_uuid,
        table_name=pick.table_name,
        partition=CompactionRoundPartitionApiResponse(spec_id=pick.spec_id, values=pick.values),
        partition_label=pick.partition_label,
        priority=cast("RoundPriorityApi", pick.priority),
        score=pick.score,
        weighted_score=pick.weighted_score,
        estimated_gb_hours=pick.estimated_gb_hours,
        overdue=pick.overdue,
    )


def _skip(skip: _Skip) -> CompactionRoundSkipApiResponse:
    return CompactionRoundSkipApiResponse(
        table_uuid=skip.table_uuid,
        table_name=skip.table_name,
        partition=CompactionRoundPartitionApiResponse(spec_id=skip.spec_id, values=skip.values),
        partition_label=skip.partition_label,
        priority=cast("RoundPriorityApi", skip.priority),
        score=skip.score,
        weighted_score=skip.weighted_score,
        estimated_gb_hours=skip.estimated_gb_hours,
        overdue=skip.overdue,
        reason=cast("RoundSkipReasonApi", skip.reason),
    )
