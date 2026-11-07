"""Define the ListCatalogsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.catalog.list_catalogs.input import (
    ListCatalogsUseCaseInput,
)
from context.catalog.application.port.inbound.catalog.list_catalogs.output import (
    ListCatalogsUseCaseOutput,
)


class ListCatalogsUseCase(UseCase[ListCatalogsUseCaseInput, ListCatalogsUseCaseOutput]):
    """List every catalog."""

    @abstractmethod
    def execute(self, request: ListCatalogsUseCaseInput) -> ListCatalogsUseCaseOutput:
        """List every catalog."""
