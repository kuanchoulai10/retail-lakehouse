"""Define the CreateGenericTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.generic_table.create_generic_table.input import (
    CreateGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.create_generic_table.output import (
    CreateGenericTableUseCaseOutput,
)


class CreateGenericTableUseCase(UseCase[CreateGenericTableUseCaseInput, CreateGenericTableUseCaseOutput]):
    """Create a generic table from the create generic table form."""

    @abstractmethod
    def execute(self, request: CreateGenericTableUseCaseInput) -> CreateGenericTableUseCaseOutput:
        """Create a generic table from the create generic table form."""
