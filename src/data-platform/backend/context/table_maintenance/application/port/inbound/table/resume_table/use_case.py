"""Define the ResumeTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.resume_table.input import (
    ResumeTableUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.resume_table.output import (
    ResumeTableUseCaseOutput,
)


class ResumeTableUseCase(UseCase[ResumeTableUseCaseInput, ResumeTableUseCaseOutput]):
    """Resume maintenance of a table."""

    @abstractmethod
    def execute(self, request: ResumeTableUseCaseInput) -> ResumeTableUseCaseOutput:
        """Resume maintenance of a table."""
