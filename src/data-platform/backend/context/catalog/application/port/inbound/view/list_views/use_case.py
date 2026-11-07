"""Define the ListViewsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.view.list_views.input import (
    ListViewsUseCaseInput,
)
from context.catalog.application.port.inbound.view.list_views.output import (
    ListViewsUseCaseOutput,
)


class ListViewsUseCase(UseCase[ListViewsUseCaseInput, ListViewsUseCaseOutput]):
    """List the Iceberg views directly in a namespace."""

    @abstractmethod
    def execute(self, request: ListViewsUseCaseInput) -> ListViewsUseCaseOutput:
        """List the Iceberg views directly in a namespace."""
