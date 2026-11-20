"""Define the GetTableSchemaComparisonService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.service.table import compare_schemas
from context.catalog.application.exceptions import NotFoundError
from context.catalog.application.port.inbound.table import (
    GetTableSchemaComparisonUseCase,
    GetTableSchemaComparisonUseCaseInput,
    GetTableSchemaComparisonUseCaseOutput,
)
from context.catalog.application.service.table.load_table import load_table
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import Schema, Table, TablesRepo


def _schema(table: Table, schema_id: int) -> Schema:
    schema = table.schema_by_id(schema_id)
    if schema is None:
        raise NotFoundError(f"schema {schema_id} not found in table {table.id.name}")
    return schema


class GetTableSchemaComparisonService(GetTableSchemaComparisonUseCase):
    """Compare a schema version of a table with another, matching fields by field id."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: GetTableSchemaComparisonUseCaseInput) -> GetTableSchemaComparisonUseCaseOutput:
        """Return every field of the schema against the chosen base, else the previous version.

        Raises NotFoundError for an unknown table, schema or base. The first version has no base.
        """
        table = load_table(self._tables_repo, table_id_from_parts(request.catalog, request.namespace, request.name))
        schema = _schema(table, request.schema_id)
        base = table.previous_schema(schema.schema_id)
        if request.base_schema_id is not None:
            base = _schema(table, request.base_schema_id)
        comparison = compare_schemas(base, schema)
        return GetTableSchemaComparisonUseCaseOutput(
            base_schema_id=comparison.base_schema_id,
            schema_id=comparison.schema_id,
            items=tuple(
                GetTableSchemaComparisonUseCaseOutput.Field(
                    field_id=field.field_id,
                    depth=field.depth,
                    path=field.path,
                    previous_path=field.previous_path,
                    type=field.type,
                    previous_type=field.previous_type,
                    required=field.required,
                    previous_required=field.previous_required,
                    doc=field.doc,
                    previous_doc=field.previous_doc,
                    changes=tuple(str(change) for change in field.changes),
                )
                for field in comparison.fields
            ),
        )
