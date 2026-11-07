"""Define the DeleteNamespaceService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.port.inbound.namespace import (
    DeleteNamespaceUseCase,
    DeleteNamespaceUseCaseInput,
    DeleteNamespaceUseCaseOutput,
)
from context.catalog.application.service.namespace.namespace_id_from_parts import (
    namespace_id_from_parts,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.namespace import NamespacesRepo


class DeleteNamespaceService(DeleteNamespaceUseCase):
    """Delete an empty namespace; one that still holds content is refused with the catalog's message."""

    def __init__(self, namespaces_repo: NamespacesRepo) -> None:
        """Bind the repo."""
        self._namespaces_repo = namespaces_repo

    def execute(self, request: DeleteNamespaceUseCaseInput) -> DeleteNamespaceUseCaseOutput:
        """Delete the namespace; the repo raises NotFoundError or ConflictError."""
        self._namespaces_repo.delete(namespace_id_from_parts(request.catalog, request.namespace))
        return DeleteNamespaceUseCaseOutput()
