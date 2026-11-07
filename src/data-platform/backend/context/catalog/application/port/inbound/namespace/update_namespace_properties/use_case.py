"""Define the UpdateNamespacePropertiesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.namespace.update_namespace_properties.input import (
    UpdateNamespacePropertiesUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.update_namespace_properties.output import (
    UpdateNamespacePropertiesUseCaseOutput,
)


class UpdateNamespacePropertiesUseCase(
    UseCase[UpdateNamespacePropertiesUseCaseInput, UpdateNamespacePropertiesUseCaseOutput]
):
    """Set and remove properties of a namespace."""

    @abstractmethod
    def execute(self, request: UpdateNamespacePropertiesUseCaseInput) -> UpdateNamespacePropertiesUseCaseOutput:
        """Set and remove properties of a namespace."""
