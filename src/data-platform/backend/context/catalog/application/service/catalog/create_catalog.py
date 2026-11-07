"""Define the CreateCatalogService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.catalog import (
    Catalog,
    CatalogId,
    CatalogType,
)
from context.catalog.application.exceptions import (
    CatalogUnavailableError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from context.catalog.application.port.inbound.catalog import (
    CreateCatalogUseCase,
    CreateCatalogUseCaseInput,
    CreateCatalogUseCaseOutput,
)
from context.catalog.application.port.outbound.catalog import (
    CreateCatalogContentGrantGatewayInput,
)
from context.catalog.application.service.catalog.catalog_output_fields import (
    catalog_output_fields,
)
from context.catalog.application.service.catalog.connection_config_from_dict import (
    connection_config_from_dict,
)
from context.catalog.application.service.catalog.storage_config_from_dict import (
    storage_config_from_dict,
)

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.catalog import (
        CatalogsRepo,
        CreateCatalogContentGrantGateway,
    )

_GRANT_ERRORS = (CatalogUnavailableError, ConflictError, NotFoundError, PermissionDeniedError, ValidationError)
_CATALOG_TYPES = ", ".join(CatalogType)


class CreateCatalogService(CreateCatalogUseCase):
    """Create a catalog, then let the catalog's own admin role manage its content.

    Without the grant, the new catalog's admin role could not create namespaces or tables,
    so every catalog made here behaves like the ones the platform bootstraps. When the grant
    fails, the catalog stays created and the failure is raised with the upstream message,
    so the caller never sees a success for a catalog that cannot hold content.
    """

    def __init__(
        self,
        catalogs_repo: CatalogsRepo,
        content_grant_gateway: CreateCatalogContentGrantGateway,
    ) -> None:
        """Bind the repo and the content grant gateway."""
        self._catalogs_repo = catalogs_repo
        self._content_grant_gateway = content_grant_gateway

    def execute(self, request: CreateCatalogUseCaseInput) -> CreateCatalogUseCaseOutput:
        """Validate the form, save the catalog and grant its content privilege."""
        name = request.name.strip()
        if not name:
            raise ValidationError("catalog name must not be blank")
        default_base_location = request.default_base_location.strip()
        if not default_base_location:
            raise ValidationError("default base location must not be blank")
        try:
            catalog_type = CatalogType(request.type)
        except ValueError:
            raise ValidationError(f"catalog type must be one of {_CATALOG_TYPES}, not {request.type!r}") from None
        storage_config = storage_config_from_dict(request.storage_config)
        connection_config = None
        if request.connection_config is not None:
            if catalog_type is not CatalogType.EXTERNAL:
                raise ValidationError("connection_config applies only to EXTERNAL catalogs")
            connection_config = connection_config_from_dict(request.connection_config)
        elif catalog_type is CatalogType.EXTERNAL:
            raise ValidationError("an EXTERNAL catalog needs a connection_config")
        created = self._catalogs_repo.create(
            Catalog.create(CatalogId.of(name), catalog_type, default_base_location, storage_config, connection_config)
        )
        try:
            self._content_grant_gateway.create(CreateCatalogContentGrantGatewayInput(catalog_name=created.name))
        except _GRANT_ERRORS as exc:
            raise type(exc)(f"catalog {created.name} was created but the content grant failed: {exc}") from exc
        return CreateCatalogUseCaseOutput(**catalog_output_fields(created))
