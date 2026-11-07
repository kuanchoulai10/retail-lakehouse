"""Define the catalog router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from context.catalog.adapter.inbound.web.catalog.dto import (
    CatalogApiResponse,
    CreateCatalogApiRequest,
    UpdateCatalogApiRequest,
)
from context.catalog.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.catalog.application.port.inbound.catalog import (
    CreateCatalogUseCaseInput,
    DeleteCatalogUseCaseInput,
    GetCatalogUseCaseInput,
    ListCatalogsUseCaseInput,
    UpdateCatalogUseCaseInput,
)

router = APIRouter(prefix="/catalogs", tags=["catalogs"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]


@router.get("")
def list_catalogs(use_cases: UseCases) -> list[CatalogApiResponse]:
    """List every catalog."""
    output = use_cases.list_catalogs.execute(ListCatalogsUseCaseInput())
    return [CatalogApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_catalog(body: CreateCatalogApiRequest, use_cases: UseCases) -> CatalogApiResponse:
    """Create a catalog and let its admin role manage its content."""
    output = use_cases.create_catalog.execute(
        CreateCatalogUseCaseInput(
            name=body.name,
            type=body.type,
            default_base_location=body.default_base_location,
            storage_config=body.storage_config.model_dump(exclude_none=True),
        )
    )
    return CatalogApiResponse.model_validate(output)


@router.get("/{catalog}")
def get_catalog(catalog: str, use_cases: UseCases) -> CatalogApiResponse:
    """Return one catalog."""
    output = use_cases.get_catalog.execute(GetCatalogUseCaseInput(name=catalog))
    return CatalogApiResponse.model_validate(output)


@router.put("/{catalog}")
def update_catalog(catalog: str, body: UpdateCatalogApiRequest, use_cases: UseCases) -> CatalogApiResponse:
    """Change a catalog's properties and storage config as of the version that was loaded."""
    output = use_cases.update_catalog.execute(
        UpdateCatalogUseCaseInput(
            name=catalog,
            entity_version=body.entity_version,
            default_base_location=body.default_base_location,
            properties=body.properties,
            storage_config=body.storage_config.model_dump(exclude_none=True),
        )
    )
    return CatalogApiResponse.model_validate(output)


@router.delete("/{catalog}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog(catalog: str, use_cases: UseCases) -> Response:
    """Delete an empty catalog."""
    use_cases.delete_catalog.execute(DeleteCatalogUseCaseInput(name=catalog))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
