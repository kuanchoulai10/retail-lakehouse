"""Define the table router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from context.catalog.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.catalog.adapter.inbound.web.table.dto import (
    CreateTableApiRequest,
    RenameTableApiRequest,
    TableApiResponse,
    TableIdentifierApiResponse,
    UpdateTablePropertiesApiRequest,
)
from context.catalog.application.port.inbound.table import (
    CreateTableUseCaseInput,
    CreateTableUseCaseInputPartitionField,
    CreateTableUseCaseInputSchemaField,
    DeleteTableUseCaseInput,
    GetTableUseCaseInput,
    ListTablesUseCaseInput,
    RenameTableUseCaseInput,
    UpdateTablePropertiesUseCaseInput,
)

router = APIRouter(prefix="/catalogs/{catalog}/namespaces/{namespace}/tables", tags=["tables"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]

_SEPARATOR = "\x1f"


def _parts(namespace: str) -> list[str]:
    """Split a path namespace, its parts joined by U+001F (%1F), into its parts."""
    return namespace.split(_SEPARATOR) if namespace else []


@router.get("")
def list_tables(catalog: str, namespace: str, use_cases: UseCases) -> list[TableIdentifierApiResponse]:
    """List the Iceberg tables directly in the namespace."""
    output = use_cases.list_tables.execute(ListTablesUseCaseInput(catalog=catalog, namespace=_parts(namespace)))
    return [TableIdentifierApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_table(catalog: str, namespace: str, body: CreateTableApiRequest, use_cases: UseCases) -> TableApiResponse:
    """Create an Iceberg table from the create table form."""
    output = use_cases.create_table.execute(
        CreateTableUseCaseInput(
            catalog=catalog,
            namespace=_parts(namespace),
            name=body.name,
            schema_fields=[
                CreateTableUseCaseInputSchemaField(name=f.name, type=f.type, required=f.required, doc=f.doc)
                for f in body.schema_fields
            ],
            partition_fields=[
                CreateTableUseCaseInputPartitionField(source_column=f.source_column, transform=f.transform)
                for f in body.partition_fields
            ],
            location=body.location,
            properties=body.properties,
        )
    )
    return TableApiResponse.model_validate(output)


@router.get("/{table}")
def get_table(catalog: str, namespace: str, table: str, use_cases: UseCases) -> TableApiResponse:
    """Return one Iceberg table with its schema, partition spec, sort order, snapshots, properties and summary."""
    output = use_cases.get_table.execute(GetTableUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=table))
    return TableApiResponse.model_validate(output)


@router.delete("/{table}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table(catalog: str, namespace: str, table: str, use_cases: UseCases) -> Response:
    """Drop the table; its files are never purged."""
    use_cases.delete_table.execute(DeleteTableUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=table))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{table}/rename")
def rename_table(
    catalog: str, namespace: str, table: str, body: RenameTableApiRequest, use_cases: UseCases
) -> TableIdentifierApiResponse:
    """Rename the table or move it to another namespace of the catalog; return where it now is."""
    output = use_cases.rename_table.execute(
        RenameTableUseCaseInput(
            catalog=catalog,
            namespace=_parts(namespace),
            name=table,
            target_namespace=body.target_namespace,
            target_name=body.target_name,
        )
    )
    return TableIdentifierApiResponse.model_validate(output)


@router.put("/{table}/properties")
def update_table_properties(
    catalog: str, namespace: str, table: str, body: UpdateTablePropertiesApiRequest, use_cases: UseCases
) -> TableApiResponse:
    """Set and remove properties of the table that was loaded; 409 when it changed since."""
    output = use_cases.update_table_properties.execute(
        UpdateTablePropertiesUseCaseInput(
            catalog=catalog,
            namespace=_parts(namespace),
            name=table,
            expected_uuid=body.expected_uuid,
            updates=body.updates,
            removals=body.removals,
        )
    )
    return TableApiResponse.model_validate(output)
