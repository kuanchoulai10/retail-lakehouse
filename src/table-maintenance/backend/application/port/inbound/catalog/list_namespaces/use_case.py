"""Define the ListNamespacesUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.list_namespaces.input import (
    ListNamespacesInput,
)
from application.port.inbound.catalog.list_namespaces.output import (
    ListNamespacesOutput,
)


class ListNamespacesUseCase(UseCase[ListNamespacesInput, ListNamespacesOutput]):
    """List all namespaces in the catalog."""
