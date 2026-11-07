"""Define the GetNamespaceService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.namespace import (
    GetNamespaceUseCase,
    GetNamespaceUseCaseInput,
    GetNamespaceUseCaseOutput,
)
from context.catalog.application.service.namespace.namespace_id_from_parts import (
    namespace_id_from_parts,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.namespace import NamespacesRepo


class GetNamespaceService(GetNamespaceUseCase):
    """Get one namespace with its properties."""

    def __init__(self, namespaces_repo: NamespacesRepo) -> None:
        """Bind the repo."""
        self._namespaces_repo = namespaces_repo

    def execute(self, request: GetNamespaceUseCaseInput) -> GetNamespaceUseCaseOutput:
        """Return the namespace or raise NotFoundError."""
        namespace = self._namespaces_repo.get(namespace_id_from_parts(request.catalog, request.namespace))
        if namespace is None:
            raise NotFoundError(f"namespace {request.namespace} not found in catalog {request.catalog}")
        return GetNamespaceUseCaseOutput(
            catalog=namespace.catalog, namespace=list(namespace.parts), properties=dict(namespace.properties)
        )
