"""Define the GetCompactionRoundService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_round import CompactionRoundId
from context.table_maintenance.application.exceptions import NotFoundError
from context.table_maintenance.application.port.inbound.compaction_round import (
    GetCompactionRoundUseCase,
    GetCompactionRoundUseCaseInput,
    GetCompactionRoundUseCaseOutput,
    GetCompactionRoundUseCaseOutputPick,
    GetCompactionRoundUseCaseOutputSkip,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.compaction_round import RoundPick, RoundSkip
    from context.table_maintenance.application.domain.model.table import TableId
    from context.table_maintenance.application.port.outbound.compaction_round import CompactionRoundsRepo
    from context.table_maintenance.application.port.outbound.table import TablesRepo


class GetCompactionRoundService(GetCompactionRoundUseCase):
    """Read one recorded compaction round, naming the tables its picks and skips belong to."""

    def __init__(self, rounds_repo: CompactionRoundsRepo, tables_repo: TablesRepo) -> None:
        """Bind the rounds and tables repos."""
        self._rounds_repo = rounds_repo
        self._tables_repo = tables_repo

    def execute(self, request: GetCompactionRoundUseCaseInput) -> GetCompactionRoundUseCaseOutput:
        """Return the round; one never recorded (or purged since) is not found."""
        round_ = self._rounds_repo.get(CompactionRoundId(request.round_id))
        if round_ is None:
            raise NotFoundError(f"compaction round {request.round_id} not found")
        names: dict[str, str | None] = {}
        for entry in (*round_.picks, *round_.skips):
            if entry.table_uuid.value not in names:
                names[entry.table_uuid.value] = self._name(entry.table_uuid)
        return GetCompactionRoundUseCaseOutput(
            round_id=round_.id.value,
            started_at=round_.started_at,
            budget_gb_hours=round_.budget_gb_hours,
            used_gb_hours=round_.used_gb_hours,
            picks=[_pick(p, names) for p in round_.picks],
            skips=[_skip(s, names) for s in round_.skips],
            skipped_total=round_.skipped_total,
        )

    def _name(self, table_uuid: TableId) -> str | None:
        table = self._tables_repo.get(table_uuid)
        return None if table is None else table.name.fully_qualified()


def _pick(pick: RoundPick, names: dict[str, str | None]) -> GetCompactionRoundUseCaseOutputPick:
    return GetCompactionRoundUseCaseOutputPick(
        table_uuid=pick.table_uuid.value,
        table_name=names.get(pick.table_uuid.value),
        spec_id=pick.partition.spec_id,
        values=list(pick.partition.values),
        partition_label=pick.label,
        priority=pick.priority.value,
        score=pick.score,
        weighted_score=pick.weighted_score,
        estimated_gb_hours=pick.estimated_gb_hours,
        overdue=pick.overdue,
    )


def _skip(skip: RoundSkip, names: dict[str, str | None]) -> GetCompactionRoundUseCaseOutputSkip:
    return GetCompactionRoundUseCaseOutputSkip(
        table_uuid=skip.table_uuid.value,
        table_name=names.get(skip.table_uuid.value),
        spec_id=skip.partition.spec_id,
        values=list(skip.partition.values),
        partition_label=skip.label,
        priority=skip.priority.value,
        score=skip.score,
        weighted_score=skip.weighted_score,
        estimated_gb_hours=skip.estimated_gb_hours,
        overdue=skip.overdue,
        reason=skip.reason.value,
    )
