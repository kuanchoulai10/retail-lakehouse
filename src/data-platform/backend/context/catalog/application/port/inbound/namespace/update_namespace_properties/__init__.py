"""Set and remove properties of a namespace."""

from context.catalog.application.port.inbound.namespace.update_namespace_properties.input import (
    UpdateNamespacePropertiesUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.update_namespace_properties.output import (
    UpdateNamespacePropertiesUseCaseOutput,
)
from context.catalog.application.port.inbound.namespace.update_namespace_properties.use_case import (
    UpdateNamespacePropertiesUseCase,
)

__all__ = [
    "UpdateNamespacePropertiesUseCase",
    "UpdateNamespacePropertiesUseCaseInput",
    "UpdateNamespacePropertiesUseCaseOutput",
]
