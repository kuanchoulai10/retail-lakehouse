"""Define the ReleaseCompactionCandidatesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.compaction_candidate.release_compaction_candidates.input import (  # noqa: E501
    ReleaseCompactionCandidatesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.compaction_candidate.release_compaction_candidates.output import (  # noqa: E501
    ReleaseCompactionCandidatesUseCaseOutput,
)


class ReleaseCompactionCandidatesUseCase(
    UseCase[ReleaseCompactionCandidatesUseCaseInput, ReleaseCompactionCandidatesUseCaseOutput]
):
    """Hand the compaction candidates a run holds back as pending."""

    @abstractmethod
    def execute(self, request: ReleaseCompactionCandidatesUseCaseInput) -> ReleaseCompactionCandidatesUseCaseOutput:
        """Hand the compaction candidates a run holds back as pending."""
