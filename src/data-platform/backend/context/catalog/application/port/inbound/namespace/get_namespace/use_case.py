"""Define the GetNamespaceUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.namespace.get_namespace.input import (
    GetNamespaceUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.get_namespace.output import (
    GetNamespaceUseCaseOutput,
)


class GetNamespaceUseCase(UseCase[GetNamespaceUseCaseInput, GetNamespaceUseCaseOutput]):
    """Get one namespace with its properties."""

    @abstractmethod
    def execute(self, request: GetNamespaceUseCaseInput) -> GetNamespaceUseCaseOutput:
        """Get one namespace with its properties."""
