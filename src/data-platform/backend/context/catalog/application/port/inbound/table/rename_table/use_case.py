"""Define the RenameTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.rename_table.input import (
    RenameTableUseCaseInput,
)
from context.catalog.application.port.inbound.table.rename_table.output import (
    RenameTableUseCaseOutput,
)


class RenameTableUseCase(UseCase[RenameTableUseCaseInput, RenameTableUseCaseOutput]):
    """Rename an Iceberg table, or move it to another namespace of its catalog."""

    @abstractmethod
    def execute(self, request: RenameTableUseCaseInput) -> RenameTableUseCaseOutput:
        """Rename an Iceberg table, or move it to another namespace of its catalog."""
