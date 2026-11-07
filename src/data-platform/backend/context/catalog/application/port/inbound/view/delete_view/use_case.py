"""Define the DeleteViewUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.view.delete_view.input import (
    DeleteViewUseCaseInput,
)
from context.catalog.application.port.inbound.view.delete_view.output import (
    DeleteViewUseCaseOutput,
)


class DeleteViewUseCase(UseCase[DeleteViewUseCaseInput, DeleteViewUseCaseOutput]):
    """Drop an Iceberg view from the catalog."""

    @abstractmethod
    def execute(self, request: DeleteViewUseCaseInput) -> DeleteViewUseCaseOutput:
        """Drop an Iceberg view from the catalog."""
