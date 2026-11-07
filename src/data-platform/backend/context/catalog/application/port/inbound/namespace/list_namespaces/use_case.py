"""Define the ListNamespacesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.namespace.list_namespaces.input import (
    ListNamespacesUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.list_namespaces.output import (
    ListNamespacesUseCaseOutput,
)


class ListNamespacesUseCase(UseCase[ListNamespacesUseCaseInput, ListNamespacesUseCaseOutput]):
    """List the direct children of a namespace, or the top level of a catalog."""

    @abstractmethod
    def execute(self, request: ListNamespacesUseCaseInput) -> ListNamespacesUseCaseOutput:
        """List the direct children of a namespace, or the top level of a catalog."""
