"""Define the ListCompactionRoundsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.port.inbound.compaction_round import (
    ListCompactionRoundsUseCase,
    ListCompactionRoundsUseCaseInput,
    ListCompactionRoundsUseCaseOutput,
    ListCompactionRoundsUseCaseOutputItem,
    ListCompactionRoundsUseCaseOutputPick,
    ListCompactionRoundsUseCaseOutputSkip,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.compaction_round import (
        CompactionRound,
        RoundPick,
        RoundSkip,
    )
    from context.table_maintenance.application.domain.model.table import TableId
    from context.table_maintenance.application.port.outbound.compaction_round import CompactionRoundsRepo
    from context.table_maintenance.application.port.outbound.table import TablesRepo


class ListCompactionRoundsService(ListCompactionRoundsUseCase):
    """List the recorded compaction rounds, newest first, naming the tables their picks and skips belong to."""

    def __init__(self, rounds_repo: CompactionRoundsRepo, tables_repo: TablesRepo) -> None:
        """Bind the rounds and tables repos."""
        self._rounds_repo = rounds_repo
        self._tables_repo = tables_repo

    def execute(self, request: ListCompactionRoundsUseCaseInput) -> ListCompactionRoundsUseCaseOutput:
        """Return up to ``limit`` rounds that started before ``before``, newest first."""
        rounds = self._rounds_repo.list_recent(limit=request.limit, before=request.before)
        names = self._names(rounds)
        return ListCompactionRoundsUseCaseOutput(items=[_item(r, names) for r in rounds])

    def _names(self, rounds: list[CompactionRound]) -> dict[str, str | None]:
        """Return the current name of every table the rounds mention, None for a table no longer known."""
        names: dict[str, str | None] = {}
        for round_ in rounds:
            for entry in (*round_.picks, *round_.skips):
                if entry.table_uuid.value not in names:
                    names[entry.table_uuid.value] = self._name(entry.table_uuid)
        return names

    def _name(self, table_uuid: TableId) -> str | None:
        table = self._tables_repo.get(table_uuid)
        return None if table is None else table.name.fully_qualified()


def _item(round_: CompactionRound, names: dict[str, str | None]) -> ListCompactionRoundsUseCaseOutputItem:
    return ListCompactionRoundsUseCaseOutputItem(
        round_id=round_.id.value,
        started_at=round_.started_at,
        budget_gb_hours=round_.budget_gb_hours,
        used_gb_hours=round_.used_gb_hours,
        picks=[_pick(p, names) for p in round_.picks],
        skips=[_skip(s, names) for s in round_.skips],
        skipped_total=round_.skipped_total,
    )


def _pick(pick: RoundPick, names: dict[str, str | None]) -> ListCompactionRoundsUseCaseOutputPick:
    return ListCompactionRoundsUseCaseOutputPick(
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


def _skip(skip: RoundSkip, names: dict[str, str | None]) -> ListCompactionRoundsUseCaseOutputSkip:
    return ListCompactionRoundsUseCaseOutputSkip(
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
