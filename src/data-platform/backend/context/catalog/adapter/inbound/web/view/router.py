"""Define the view router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from context.catalog.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.catalog.adapter.inbound.web.view.dto import (
    CreateViewApiRequest,
    ViewApiResponse,
    ViewIdentifierApiResponse,
)
from context.catalog.application.port.inbound.view import (
    CreateViewUseCaseInput,
    DeleteViewUseCaseInput,
    GetViewUseCaseInput,
    ListViewsUseCaseInput,
)

router = APIRouter(prefix="/catalogs/{catalog}/namespaces/{namespace}/views", tags=["views"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]

_SEPARATOR = "\x1f"


def _parts(namespace: str) -> list[str]:
    """Split a path namespace, its parts joined by U+001F (%1F), into its parts."""
    return namespace.split(_SEPARATOR) if namespace else []


@router.get("")
def list_views(catalog: str, namespace: str, use_cases: UseCases) -> list[ViewIdentifierApiResponse]:
    """List the Iceberg views directly in the namespace."""
    output = use_cases.list_views.execute(ListViewsUseCaseInput(catalog=catalog, namespace=_parts(namespace)))
    return [ViewIdentifierApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_view(catalog: str, namespace: str, body: CreateViewApiRequest, use_cases: UseCases) -> ViewApiResponse:
    """Create an Iceberg view from the create view form."""
    output = use_cases.create_view.execute(
        CreateViewUseCaseInput(
            catalog=catalog, namespace=_parts(namespace), name=body.name, query=body.sql, dialect=body.dialect
        )
    )
    return ViewApiResponse.model_validate(output)


@router.get("/{view}")
def get_view(catalog: str, namespace: str, view: str, use_cases: UseCases) -> ViewApiResponse:
    """Return one Iceberg view with its sql, schema, versions and properties."""
    output = use_cases.get_view.execute(GetViewUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=view))
    return ViewApiResponse.model_validate(output)


@router.delete("/{view}", status_code=status.HTTP_204_NO_CONTENT)
def delete_view(catalog: str, namespace: str, view: str, use_cases: UseCases) -> Response:
    """Drop the view."""
    use_cases.delete_view.execute(DeleteViewUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=view))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
