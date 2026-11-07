"""Define the ExcludeTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.exclude_table.input import (
    ExcludeTableUseCaseInput,
)
from application.port.inbound.table.exclude_table.output import (
    ExcludeTableUseCaseOutput,
)
from base import UseCase


class ExcludeTableUseCase(UseCase[ExcludeTableUseCaseInput, ExcludeTableUseCaseOutput]):
    """Exclude a table from maintenance by hand."""

    @abstractmethod
    def execute(self, request: ExcludeTableUseCaseInput) -> ExcludeTableUseCaseOutput:
        """Exclude a table from maintenance by hand."""
