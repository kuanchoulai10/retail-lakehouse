"""Define the CreateTableUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.create_table.input import (
    CreateTableUseCaseInput,
)
from context.catalog.application.port.inbound.table.create_table.output import (
    CreateTableUseCaseOutput,
)


class CreateTableUseCase(UseCase[CreateTableUseCaseInput, CreateTableUseCaseOutput]):
    """Create an Iceberg table from the create table form."""

    @abstractmethod
    def execute(self, request: CreateTableUseCaseInput) -> CreateTableUseCaseOutput:
        """Create an Iceberg table from the create table form."""
