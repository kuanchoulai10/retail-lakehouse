"""Define the generic table router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from context.catalog.adapter.inbound.web.generic_table.dto import (
    CreateGenericTableApiRequest,
    GenericTableApiResponse,
    GenericTableIdentifierApiResponse,
)
from context.catalog.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.catalog.application.port.inbound.generic_table import (
    CreateGenericTableUseCaseInput,
    DeleteGenericTableUseCaseInput,
    GetGenericTableUseCaseInput,
    ListGenericTablesUseCaseInput,
)

router = APIRouter(prefix="/catalogs/{catalog}/namespaces/{namespace}/generic-tables", tags=["generic-tables"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]

_SEPARATOR = "\x1f"


def _parts(namespace: str) -> list[str]:
    """Split a path namespace, its parts joined by U+001F (%1F), into its parts."""
    return namespace.split(_SEPARATOR) if namespace else []


@router.get("")
def list_generic_tables(catalog: str, namespace: str, use_cases: UseCases) -> list[GenericTableIdentifierApiResponse]:
    """List the generic tables directly in the namespace."""
    output = use_cases.list_generic_tables.execute(
        ListGenericTablesUseCaseInput(catalog=catalog, namespace=_parts(namespace))
    )
    return [GenericTableIdentifierApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_generic_table(
    catalog: str, namespace: str, body: CreateGenericTableApiRequest, use_cases: UseCases
) -> GenericTableApiResponse:
    """Create a generic table from the create generic table form."""
    output = use_cases.create_generic_table.execute(
        CreateGenericTableUseCaseInput(
            catalog=catalog,
            namespace=_parts(namespace),
            name=body.name,
            format=body.format,
            base_location=body.base_location,
            doc=body.doc,
            properties=body.properties,
        )
    )
    return GenericTableApiResponse.model_validate(output)


@router.get("/{generic_table}")
def get_generic_table(catalog: str, namespace: str, generic_table: str, use_cases: UseCases) -> GenericTableApiResponse:
    """Return one generic table with its format, base location, doc and properties."""
    output = use_cases.get_generic_table.execute(
        GetGenericTableUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=generic_table)
    )
    return GenericTableApiResponse.model_validate(output)


@router.delete("/{generic_table}", status_code=status.HTTP_204_NO_CONTENT)
def delete_generic_table(catalog: str, namespace: str, generic_table: str, use_cases: UseCases) -> Response:
    """Drop the generic table."""
    use_cases.delete_generic_table.execute(
        DeleteGenericTableUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=generic_table)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
