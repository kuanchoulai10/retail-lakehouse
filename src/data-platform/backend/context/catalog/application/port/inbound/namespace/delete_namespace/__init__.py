"""Delete an empty namespace."""

from context.catalog.application.port.inbound.namespace.delete_namespace.input import (
    DeleteNamespaceUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.delete_namespace.output import (
    DeleteNamespaceUseCaseOutput,
)
from context.catalog.application.port.inbound.namespace.delete_namespace.use_case import (
    DeleteNamespaceUseCase,
)

__all__ = [
    "DeleteNamespaceUseCase",
    "DeleteNamespaceUseCaseInput",
    "DeleteNamespaceUseCaseOutput",
]
