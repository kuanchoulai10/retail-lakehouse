"""Define the CreateNamespaceService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.namespace import Namespace
from context.catalog.application.port.inbound.namespace import (
    CreateNamespaceUseCase,
    CreateNamespaceUseCaseInput,
    CreateNamespaceUseCaseOutput,
)
from context.catalog.application.service.namespace.namespace_id_from_parts import (
    namespace_id_from_parts,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.namespace import NamespacesRepo


class CreateNamespaceService(CreateNamespaceUseCase):
    """Create a namespace with its properties; the parent of a nested one must exist."""

    def __init__(self, namespaces_repo: NamespacesRepo) -> None:
        """Bind the repo."""
        self._namespaces_repo = namespaces_repo

    def execute(self, request: CreateNamespaceUseCaseInput) -> CreateNamespaceUseCaseOutput:
        """Validate the parts, save the namespace and return it as saved."""
        namespace_id = namespace_id_from_parts(request.catalog, request.namespace)
        saved = self._namespaces_repo.create(Namespace(id=namespace_id, properties=dict(request.properties)))
        return CreateNamespaceUseCaseOutput(
            catalog=saved.catalog, namespace=list(saved.parts), properties=dict(saved.properties)
        )
