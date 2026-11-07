"""Define the UpdateNamespacePropertiesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.inbound.namespace import (
    UpdateNamespacePropertiesUseCase,
    UpdateNamespacePropertiesUseCaseInput,
    UpdateNamespacePropertiesUseCaseOutput,
)
from context.catalog.application.service.namespace.namespace_id_from_parts import (
    namespace_id_from_parts,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.namespace import NamespacesRepo


class UpdateNamespacePropertiesService(UpdateNamespacePropertiesUseCase):
    """Set and remove properties of a namespace in one change."""

    def __init__(self, namespaces_repo: NamespacesRepo) -> None:
        """Bind the repo."""
        self._namespaces_repo = namespaces_repo

    def execute(self, request: UpdateNamespacePropertiesUseCaseInput) -> UpdateNamespacePropertiesUseCaseOutput:
        """Refuse a key that is both set and removed, then apply the change."""
        namespace_id = namespace_id_from_parts(request.catalog, request.namespace)
        both = sorted(set(request.updates) & set(request.removals))
        if both:
            raise ValidationError(f"properties cannot be both updated and removed: {', '.join(both)}")
        saved = self._namespaces_repo.update_properties(namespace_id, dict(request.updates), list(request.removals))
        return UpdateNamespacePropertiesUseCaseOutput(
            catalog=saved.catalog, namespace=list(saved.parts), properties=dict(saved.properties)
        )
