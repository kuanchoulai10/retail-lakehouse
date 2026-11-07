"""Define the CreateNamespaceUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.namespace.create_namespace.input import (
    CreateNamespaceUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.create_namespace.output import (
    CreateNamespaceUseCaseOutput,
)


class CreateNamespaceUseCase(UseCase[CreateNamespaceUseCaseInput, CreateNamespaceUseCaseOutput]):
    """Create a namespace with its properties."""

    @abstractmethod
    def execute(self, request: CreateNamespaceUseCaseInput) -> CreateNamespaceUseCaseOutput:
        """Create a namespace with its properties."""
