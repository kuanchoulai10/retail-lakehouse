"""Define the IncludeTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.include_table.input import (
    IncludeTableUseCaseInput,
)
from application.port.inbound.table.include_table.output import (
    IncludeTableUseCaseOutput,
)
from base.use_case import UseCase


class IncludeTableUseCase(UseCase[IncludeTableUseCaseInput, IncludeTableUseCaseOutput]):
    """Include a table in maintenance by hand."""

    @abstractmethod
    def execute(self, request: IncludeTableUseCaseInput) -> IncludeTableUseCaseOutput:
        """Include a table in maintenance by hand."""
