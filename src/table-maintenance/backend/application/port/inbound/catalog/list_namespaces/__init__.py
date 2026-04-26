"""ListNamespaces use case definition."""

from application.port.inbound.catalog.list_namespaces.input import (
    ListNamespacesInput,
)
from application.port.inbound.catalog.list_namespaces.output import (
    ListNamespacesOutput,
)
from application.port.inbound.catalog.list_namespaces.use_case import (
    ListNamespacesUseCase,
)

__all__ = ["ListNamespacesInput", "ListNamespacesOutput", "ListNamespacesUseCase"]
