"""Define the CreateCatalogUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.catalog.create_catalog.input import (
    CreateCatalogUseCaseInput,
)
from context.catalog.application.port.inbound.catalog.create_catalog.output import (
    CreateCatalogUseCaseOutput,
)


class CreateCatalogUseCase(UseCase[CreateCatalogUseCaseInput, CreateCatalogUseCaseOutput]):
    """Create a catalog and let its admin role manage its content."""

    @abstractmethod
    def execute(self, request: CreateCatalogUseCaseInput) -> CreateCatalogUseCaseOutput:
        """Create a catalog and let its admin role manage its content."""
