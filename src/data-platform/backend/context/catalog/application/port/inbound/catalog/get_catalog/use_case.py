"""Define the GetCatalogUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.catalog.get_catalog.input import (
    GetCatalogUseCaseInput,
)
from context.catalog.application.port.inbound.catalog.get_catalog.output import (
    GetCatalogUseCaseOutput,
)


class GetCatalogUseCase(UseCase[GetCatalogUseCaseInput, GetCatalogUseCaseOutput]):
    """Get one catalog."""

    @abstractmethod
    def execute(self, request: GetCatalogUseCaseInput) -> GetCatalogUseCaseOutput:
        """Get one catalog."""
