"""Define the ScheduleCompactionRoundUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.compaction_round.schedule_compaction_round.input import (
    ScheduleCompactionRoundUseCaseInput,
)
from context.table_maintenance.application.port.inbound.compaction_round.schedule_compaction_round.output import (
    ScheduleCompactionRoundUseCaseOutput,
)


class ScheduleCompactionRoundUseCase(
    UseCase[ScheduleCompactionRoundUseCaseInput, ScheduleCompactionRoundUseCaseOutput]
):
    """Run one compaction round: rank pending candidates across tables and grant what the budget allows."""

    @abstractmethod
    def execute(self, request: ScheduleCompactionRoundUseCaseInput) -> ScheduleCompactionRoundUseCaseOutput:
        """Run one compaction round: rank pending candidates across tables and grant what the budget allows."""
