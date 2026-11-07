"""Define the ResumeTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table.resume_table.input import (
    ResumeTableUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.resume_table.output import (
    ResumeTableUseCaseOutput,
)
from base import UseCase


class ResumeTableUseCase(UseCase[ResumeTableUseCaseInput, ResumeTableUseCaseOutput]):
    """Resume maintenance of a table."""

    @abstractmethod
    def execute(self, request: ResumeTableUseCaseInput) -> ResumeTableUseCaseOutput:
        """Resume maintenance of a table."""
