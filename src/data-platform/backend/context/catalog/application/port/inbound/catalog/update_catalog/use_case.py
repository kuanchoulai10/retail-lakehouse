"""Define the UpdateCatalogUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.catalog.update_catalog.input import (
    UpdateCatalogUseCaseInput,
)
from context.catalog.application.port.inbound.catalog.update_catalog.output import (
    UpdateCatalogUseCaseOutput,
)


class UpdateCatalogUseCase(UseCase[UpdateCatalogUseCaseInput, UpdateCatalogUseCaseOutput]):
    """Change a catalog's properties and storage config, guarding against lost writes."""

    @abstractmethod
    def execute(self, request: UpdateCatalogUseCaseInput) -> UpdateCatalogUseCaseOutput:
        """Change a catalog's properties and storage config, guarding against lost writes."""
