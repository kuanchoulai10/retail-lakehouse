"""Define the ListNamespacesUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.list_namespaces.input import (
    ListNamespacesUseCaseInput,
)
from application.port.inbound.catalog.list_namespaces.output import (
    ListNamespacesUseCaseOutput,
)


class ListNamespacesUseCase(
    UseCase[ListNamespacesUseCaseInput, ListNamespacesUseCaseOutput]
):
    """List all namespaces in the catalog."""
