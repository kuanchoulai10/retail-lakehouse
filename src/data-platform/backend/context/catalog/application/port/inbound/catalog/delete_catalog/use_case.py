"""Define the DeleteCatalogUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.catalog.delete_catalog.input import (
    DeleteCatalogUseCaseInput,
)
from context.catalog.application.port.inbound.catalog.delete_catalog.output import (
    DeleteCatalogUseCaseOutput,
)


class DeleteCatalogUseCase(UseCase[DeleteCatalogUseCaseInput, DeleteCatalogUseCaseOutput]):
    """Delete an empty catalog."""

    @abstractmethod
    def execute(self, request: DeleteCatalogUseCaseInput) -> DeleteCatalogUseCaseOutput:
        """Delete an empty catalog."""
