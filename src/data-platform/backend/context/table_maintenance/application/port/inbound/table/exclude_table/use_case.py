"""Define the ExcludeTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.exclude_table.input import (
    ExcludeTableUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.exclude_table.output import (
    ExcludeTableUseCaseOutput,
)


class ExcludeTableUseCase(UseCase[ExcludeTableUseCaseInput, ExcludeTableUseCaseOutput]):
    """Exclude a table from maintenance by hand."""

    @abstractmethod
    def execute(self, request: ExcludeTableUseCaseInput) -> ExcludeTableUseCaseOutput:
        """Exclude a table from maintenance by hand."""
