"""Get one namespace with its properties."""

from context.catalog.application.port.inbound.namespace.get_namespace.input import (
    GetNamespaceUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.get_namespace.output import (
    GetNamespaceUseCaseOutput,
)
from context.catalog.application.port.inbound.namespace.get_namespace.use_case import (
    GetNamespaceUseCase,
)

__all__ = [
    "GetNamespaceUseCase",
    "GetNamespaceUseCaseInput",
    "GetNamespaceUseCaseOutput",
]
