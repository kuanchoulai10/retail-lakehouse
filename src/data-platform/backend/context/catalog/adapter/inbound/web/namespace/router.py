"""Define the namespace router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from context.catalog.adapter.inbound.web.namespace.dto import (
    CreateNamespaceApiRequest,
    NamespaceApiResponse,
    NamespaceSummaryApiResponse,
    UpdateNamespacePropertiesApiRequest,
)
from context.catalog.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.catalog.application.port.inbound.namespace import (
    CreateNamespaceUseCaseInput,
    DeleteNamespaceUseCaseInput,
    GetNamespaceUseCaseInput,
    ListNamespacesUseCaseInput,
    UpdateNamespacePropertiesUseCaseInput,
)

router = APIRouter(prefix="/catalogs/{catalog}/namespaces", tags=["namespaces"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]

_SEPARATOR = "\x1f"


def _parts(namespace: str) -> list[str]:
    """Split a path or query namespace into its parts; the empty string is the top level."""
    return namespace.split(_SEPARATOR) if namespace else []


@router.get("")
def list_namespaces(
    catalog: str,
    use_cases: UseCases,
    parent: Annotated[str, Query(description="Parent parts joined by U+001F (%1F); empty for the top level")] = "",
) -> list[NamespaceSummaryApiResponse]:
    """List the direct children of a namespace, or the top level of the catalog."""
    output = use_cases.list_namespaces.execute(ListNamespacesUseCaseInput(catalog=catalog, parent=_parts(parent)))
    return [NamespaceSummaryApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_namespace(catalog: str, body: CreateNamespaceApiRequest, use_cases: UseCases) -> NamespaceApiResponse:
    """Create a namespace with its properties."""
    output = use_cases.create_namespace.execute(
        CreateNamespaceUseCaseInput(catalog=catalog, namespace=body.namespace, properties=body.properties)
    )
    return NamespaceApiResponse.model_validate(output)


@router.get("/{namespace}")
def get_namespace(catalog: str, namespace: str, use_cases: UseCases) -> NamespaceApiResponse:
    """Return one namespace; ``namespace`` is its parts joined by U+001F (%1F)."""
    output = use_cases.get_namespace.execute(GetNamespaceUseCaseInput(catalog=catalog, namespace=_parts(namespace)))
    return NamespaceApiResponse.model_validate(output)


@router.delete("/{namespace}", status_code=status.HTTP_204_NO_CONTENT)
def delete_namespace(catalog: str, namespace: str, use_cases: UseCases) -> Response:
    """Delete an empty namespace."""
    use_cases.delete_namespace.execute(DeleteNamespaceUseCaseInput(catalog=catalog, namespace=_parts(namespace)))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/{namespace}/properties")
def update_namespace_properties(
    catalog: str, namespace: str, body: UpdateNamespacePropertiesApiRequest, use_cases: UseCases
) -> NamespaceApiResponse:
    """Set and remove properties of a namespace."""
    output = use_cases.update_namespace_properties.execute(
        UpdateNamespacePropertiesUseCaseInput(
            catalog=catalog, namespace=_parts(namespace), updates=body.updates, removals=body.removals
        )
    )
    return NamespaceApiResponse.model_validate(output)
