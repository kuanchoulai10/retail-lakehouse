"""Define the ListCompactionCandidatesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.compaction_candidate.list_compaction_candidates.input import (
    ListCompactionCandidatesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.compaction_candidate.list_compaction_candidates.output import (
    ListCompactionCandidatesUseCaseOutput,
)


class ListCompactionCandidatesUseCase(
    UseCase[ListCompactionCandidatesUseCaseInput, ListCompactionCandidatesUseCaseOutput]
):
    """List the compaction candidates of a table."""

    @abstractmethod
    def execute(self, request: ListCompactionCandidatesUseCaseInput) -> ListCompactionCandidatesUseCaseOutput:
        """List the compaction candidates of a table."""
