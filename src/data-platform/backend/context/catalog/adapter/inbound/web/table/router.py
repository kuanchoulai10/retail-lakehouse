"""Define the table router."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, Response, status

from context.catalog.adapter.inbound.web.shared import (
    WebUseCases,
    use_cases_dependency,
)
from context.catalog.adapter.inbound.web.table.change_counts_response import change_counts_response
from context.catalog.adapter.inbound.web.table.dto import (
    CatalogTableApiResponse,
    CatalogTablePartitionSpecComparisonApiResponse,
    CatalogTablePartitionSpecVersionApiResponse,
    CatalogTablePartitionSpecVersionsApiResponse,
    CatalogTablePropertiesApiResponse,
    CatalogTablePropertyApiResponse,
    CatalogTableSchemaComparisonApiResponse,
    CatalogTableSchemaVersionApiResponse,
    CatalogTableSchemaVersionsApiResponse,
    CreateTableApiRequest,
    PartitionChangeCountsApiResponse,
    RenameTableApiRequest,
    ResetTablePropertiesApiRequest,
    SchemaChangeCountsApiResponse,
    SchemaFieldComparisonApiResponse,
    TableIdentifierApiResponse,
    UpdateTablePropertiesApiRequest,
)
from context.catalog.adapter.inbound.web.table.partition_field_comparison_response import (
    partition_field_comparison_response,
)
from context.catalog.application.port.inbound.table import (
    CreateTableUseCaseInput,
    DeleteTableUseCaseInput,
    GetTablePartitionSpecComparisonUseCaseInput,
    GetTableSchemaComparisonUseCaseInput,
    GetTableUseCaseInput,
    ListTablePartitionSpecVersionsUseCaseInput,
    ListTablePropertiesUseCaseInput,
    ListTableSchemaVersionsUseCaseInput,
    ListTablesUseCaseInput,
    RenameTableUseCaseInput,
    ResetTablePropertiesUseCaseInput,
    UpdateTablePropertiesUseCaseInput,
)

if TYPE_CHECKING:
    from context.catalog.application.port.inbound.table import (
        ListTablePropertiesUseCaseOutput,
        ResetTablePropertiesUseCaseOutput,
    )

router = APIRouter(prefix="/catalogs/{catalog}/namespaces/{namespace}/tables", tags=["tables"])

UseCases = Annotated[WebUseCases, Depends(use_cases_dependency)]

_SEPARATOR = "\x1f"


def _parts(namespace: str) -> tuple[str, ...]:
    """Split a path namespace, its parts joined by U+001F (%1F), into its parts."""
    return tuple(namespace.split(_SEPARATOR)) if namespace else ()


def _properties_response(
    output: ListTablePropertiesUseCaseOutput | ResetTablePropertiesUseCaseOutput,
) -> CatalogTablePropertiesApiResponse:
    return CatalogTablePropertiesApiResponse(
        uuid=output.uuid,
        iceberg_version=output.iceberg_version,
        properties=[CatalogTablePropertyApiResponse.model_validate(item) for item in output.items],
    )


@router.get("", name="list_catalog_tables")
def list_tables(catalog: str, namespace: str, use_cases: UseCases) -> list[TableIdentifierApiResponse]:
    """List the Iceberg tables directly in the namespace."""
    output = use_cases.list_tables.execute(ListTablesUseCaseInput(catalog=catalog, namespace=_parts(namespace)))
    return [TableIdentifierApiResponse.model_validate(item) for item in output.items]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_table(
    catalog: str, namespace: str, body: CreateTableApiRequest, use_cases: UseCases
) -> CatalogTableApiResponse:
    """Create an Iceberg table from the create table form."""
    output = use_cases.create_table.execute(
        CreateTableUseCaseInput(
            catalog=catalog,
            namespace=_parts(namespace),
            name=body.name,
            schema_fields=tuple(
                CreateTableUseCaseInput.SchemaField(name=f.name, type=f.type, required=f.required, doc=f.doc)
                for f in body.schema_fields
            ),
            partition_fields=tuple(
                CreateTableUseCaseInput.PartitionField(source_column=f.source_column, transform=f.transform)
                for f in body.partition_fields
            ),
            location=body.location,
            properties=body.properties,
        )
    )
    return CatalogTableApiResponse.model_validate(output)


@router.get("/{table}", name="get_catalog_table")
def get_table(catalog: str, namespace: str, table: str, use_cases: UseCases) -> CatalogTableApiResponse:
    """Return one Iceberg table with its schema, partition spec, sort order, snapshots, properties and summary."""
    output = use_cases.get_table.execute(GetTableUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=table))
    return CatalogTableApiResponse.model_validate(output)


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
            target_namespace=tuple(body.target_namespace),
            target_name=body.target_name,
        )
    )
    return TableIdentifierApiResponse.model_validate(output)


@router.put("/{table}/properties")
def update_table_properties(
    catalog: str, namespace: str, table: str, body: UpdateTablePropertiesApiRequest, use_cases: UseCases
) -> CatalogTableApiResponse:
    """Set and remove properties of the table that was loaded; 409 when it changed since."""
    output = use_cases.update_table_properties.execute(
        UpdateTablePropertiesUseCaseInput(
            catalog=catalog,
            namespace=_parts(namespace),
            name=table,
            expected_uuid=body.expected_uuid,
            updates=body.updates,
            removals=tuple(body.removals),
        )
    )
    return CatalogTableApiResponse.model_validate(output)


@router.get("/{table}/properties", name="list_catalog_table_properties")
def list_table_properties(
    catalog: str, namespace: str, table: str, use_cases: UseCases
) -> CatalogTablePropertiesApiResponse:
    """Return every property of the table next to its default (Iceberg's or the catalog's), ordered by key."""
    output = use_cases.list_table_properties.execute(
        ListTablePropertiesUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=table)
    )
    return _properties_response(output)


@router.post("/{table}/properties/reset", name="reset_catalog_table_properties")
def reset_table_properties(
    catalog: str, namespace: str, table: str, body: ResetTablePropertiesApiRequest, use_cases: UseCases
) -> CatalogTablePropertiesApiResponse:
    """Reset properties of the loaded table to default; 422 for one not resettable, 409 when the table changed."""
    output = use_cases.reset_table_properties.execute(
        ResetTablePropertiesUseCaseInput(
            catalog=catalog,
            namespace=_parts(namespace),
            name=table,
            expected_uuid=body.expected_uuid,
            keys=tuple(body.keys),
        )
    )
    return _properties_response(output)


@router.get("/{table}/schema-versions", name="list_catalog_table_schema_versions")
def list_table_schema_versions(
    catalog: str, namespace: str, table: str, use_cases: UseCases
) -> CatalogTableSchemaVersionsApiResponse:
    """Return every schema version of the table, newest id first, each with what it changed against the one below."""
    output = use_cases.list_table_schema_versions.execute(
        ListTableSchemaVersionsUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=table)
    )
    return CatalogTableSchemaVersionsApiResponse(
        current_schema_id=output.current_schema_id,
        versions=[
            CatalogTableSchemaVersionApiResponse(
                schema_id=item.schema_id,
                previous_schema_id=item.previous_schema_id,
                current=item.current,
                column_count=item.column_count,
                changes=change_counts_response(SchemaChangeCountsApiResponse, item.changes),
            )
            for item in output.items
        ],
    )


@router.get("/{table}/schema-versions/{schema_id}/comparison", name="get_catalog_table_schema_comparison")
def get_table_schema_comparison(
    catalog: str, namespace: str, table: str, schema_id: int, use_cases: UseCases, base: int | None = None
) -> CatalogTableSchemaComparisonApiResponse:
    """Return every field of a schema version set against ``base``, else the previous version, matched by field id."""
    output = use_cases.get_table_schema_comparison.execute(
        GetTableSchemaComparisonUseCaseInput(
            catalog=catalog, namespace=_parts(namespace), name=table, schema_id=schema_id, base_schema_id=base
        )
    )
    return CatalogTableSchemaComparisonApiResponse(
        base_schema_id=output.base_schema_id,
        schema_id=output.schema_id,
        fields=[SchemaFieldComparisonApiResponse.model_validate(item) for item in output.items],
    )


@router.get("/{table}/partition-spec-versions", name="list_catalog_table_partition_spec_versions")
def list_table_partition_spec_versions(
    catalog: str, namespace: str, table: str, use_cases: UseCases
) -> CatalogTablePartitionSpecVersionsApiResponse:
    """Return every partition spec version of the table, newest id first, each with what it changed."""
    output = use_cases.list_table_partition_spec_versions.execute(
        ListTablePartitionSpecVersionsUseCaseInput(catalog=catalog, namespace=_parts(namespace), name=table)
    )
    return CatalogTablePartitionSpecVersionsApiResponse(
        default_spec_id=output.default_spec_id,
        versions=[
            CatalogTablePartitionSpecVersionApiResponse(
                spec_id=item.spec_id,
                previous_spec_id=item.previous_spec_id,
                default=item.default,
                field_count=item.field_count,
                changes=change_counts_response(PartitionChangeCountsApiResponse, item.changes),
            )
            for item in output.items
        ],
    )


@router.get("/{table}/partition-spec-versions/{spec_id}/comparison", name="get_catalog_table_partition_spec_comparison")
def get_table_partition_spec_comparison(
    catalog: str, namespace: str, table: str, spec_id: int, use_cases: UseCases, base: int | None = None
) -> CatalogTablePartitionSpecComparisonApiResponse:
    """Return every field of a partition spec version set against ``base``, else the previous version."""
    output = use_cases.get_table_partition_spec_comparison.execute(
        GetTablePartitionSpecComparisonUseCaseInput(
            catalog=catalog, namespace=_parts(namespace), name=table, spec_id=spec_id, base_spec_id=base
        )
    )
    return CatalogTablePartitionSpecComparisonApiResponse(
        base_spec_id=output.base_spec_id,
        spec_id=output.spec_id,
        fields=[partition_field_comparison_response(item) for item in output.items],
    )
