"""Define the ListCompactionRoundsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.compaction_round.list_compaction_rounds.input import (
    ListCompactionRoundsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.compaction_round.list_compaction_rounds.output import (
    ListCompactionRoundsUseCaseOutput,
)


class ListCompactionRoundsUseCase(UseCase[ListCompactionRoundsUseCaseInput, ListCompactionRoundsUseCaseOutput]):
    """List the recorded compaction rounds, newest first."""

    @abstractmethod
    def execute(self, request: ListCompactionRoundsUseCaseInput) -> ListCompactionRoundsUseCaseOutput:
        """List the recorded compaction rounds, newest first."""
