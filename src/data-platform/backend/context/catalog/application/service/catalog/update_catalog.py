"""Define the UpdateCatalogService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.catalog import CatalogId
from context.catalog.application.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from context.catalog.application.port.inbound.catalog import (
    UpdateCatalogUseCase,
    UpdateCatalogUseCaseInput,
    UpdateCatalogUseCaseOutput,
)
from context.catalog.application.service.catalog.catalog_output_fields import (
    catalog_output_fields,
)
from context.catalog.application.service.catalog.storage_config_from_dict import (
    storage_config_from_dict,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import CatalogsRepo


class UpdateCatalogService(UpdateCatalogUseCase):
    """Change a catalog's properties and storage config as of the version the caller loaded."""

    def __init__(self, catalogs_repo: CatalogsRepo) -> None:
        """Bind the repo."""
        self._catalogs_repo = catalogs_repo

    def execute(self, request: UpdateCatalogUseCaseInput) -> UpdateCatalogUseCaseOutput:
        """Save the change; a catalog changed since the caller loaded it is a conflict to reload."""
        default_base_location = request.default_base_location.strip()
        if not default_base_location:
            raise ValidationError("default base location must not be blank")
        storage_config = storage_config_from_dict(request.storage_config)
        catalog = self._catalogs_repo.get(CatalogId.of(request.name))
        if catalog is None:
            raise NotFoundError(f"catalog {request.name} not found")
        catalog.reconfigure(
            default_base_location=default_base_location,
            properties=request.properties,
            storage_config=storage_config,
            loaded_version=request.entity_version,
        )
        try:
            saved = self._catalogs_repo.update(catalog)
        except ConflictError as exc:
            raise ConflictError(f"catalog {request.name} changed since you loaded it, reload") from exc
        return UpdateCatalogUseCaseOutput(**catalog_output_fields(saved))
