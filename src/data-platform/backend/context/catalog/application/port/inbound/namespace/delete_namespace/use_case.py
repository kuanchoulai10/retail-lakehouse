"""Define the DeleteNamespaceUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.namespace.delete_namespace.input import (
    DeleteNamespaceUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.delete_namespace.output import (
    DeleteNamespaceUseCaseOutput,
)


class DeleteNamespaceUseCase(UseCase[DeleteNamespaceUseCaseInput, DeleteNamespaceUseCaseOutput]):
    """Delete an empty namespace."""

    @abstractmethod
    def execute(self, request: DeleteNamespaceUseCaseInput) -> DeleteNamespaceUseCaseOutput:
        """Delete an empty namespace."""
