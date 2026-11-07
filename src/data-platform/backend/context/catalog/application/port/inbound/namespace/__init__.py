"""Inbound ports for the namespace group."""

from __future__ import annotations

from context.catalog.application.port.inbound.namespace.create_namespace.input import (
    CreateNamespaceUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.create_namespace.output import (
    CreateNamespaceUseCaseOutput,
)
from context.catalog.application.port.inbound.namespace.create_namespace.use_case import (
    CreateNamespaceUseCase,
)
from context.catalog.application.port.inbound.namespace.delete_namespace.input import (
    DeleteNamespaceUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.delete_namespace.output import (
    DeleteNamespaceUseCaseOutput,
)
from context.catalog.application.port.inbound.namespace.delete_namespace.use_case import (
    DeleteNamespaceUseCase,
)
from context.catalog.application.port.inbound.namespace.get_namespace.input import (
    GetNamespaceUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.get_namespace.output import (
    GetNamespaceUseCaseOutput,
)
from context.catalog.application.port.inbound.namespace.get_namespace.use_case import (
    GetNamespaceUseCase,
)
from context.catalog.application.port.inbound.namespace.list_namespaces.input import (
    ListNamespacesUseCaseInput,
)
from context.catalog.application.port.inbound.namespace.list_namespaces.output import (
    ListNamespacesUseCaseOutput,
    ListNamespacesUseCaseOutputItem,
)
from context.catalog.application.port.inbound.namespace.list_namespaces.use_case import (
    ListNamespacesUseCase,
)
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
    "CreateNamespaceUseCase",
    "CreateNamespaceUseCaseInput",
    "CreateNamespaceUseCaseOutput",
    "DeleteNamespaceUseCase",
    "DeleteNamespaceUseCaseInput",
    "DeleteNamespaceUseCaseOutput",
    "GetNamespaceUseCase",
    "GetNamespaceUseCaseInput",
    "GetNamespaceUseCaseOutput",
    "ListNamespacesUseCase",
    "ListNamespacesUseCaseInput",
    "ListNamespacesUseCaseOutput",
    "ListNamespacesUseCaseOutputItem",
    "UpdateNamespacePropertiesUseCase",
    "UpdateNamespacePropertiesUseCaseInput",
    "UpdateNamespacePropertiesUseCaseOutput",
]
