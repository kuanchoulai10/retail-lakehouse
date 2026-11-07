"""Define the CreateViewUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.view.create_view.input import (
    CreateViewUseCaseInput,
)
from context.catalog.application.port.inbound.view.create_view.output import (
    CreateViewUseCaseOutput,
)


class CreateViewUseCase(UseCase[CreateViewUseCaseInput, CreateViewUseCaseOutput]):
    """Create an Iceberg view from the create view form."""

    @abstractmethod
    def execute(self, request: CreateViewUseCaseInput) -> CreateViewUseCaseOutput:
        """Create an Iceberg view from the create view form."""
