"""Define the ListTableSchemaVersionsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.service.table import compare_schemas
from context.catalog.application.port.inbound.table import (
    ListTableSchemaVersionsUseCase,
    ListTableSchemaVersionsUseCaseInput,
    ListTableSchemaVersionsUseCaseOutput,
)
from context.catalog.application.service.table.load_table import load_table
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import Schema, Table, TablesRepo


def _version(table: Table, schema: Schema) -> ListTableSchemaVersionsUseCaseOutput.Version:
    previous = table.previous_schema(schema.schema_id)
    changes = None
    if previous is not None:
        counts = compare_schemas(previous, schema).change_counts()
        changes = {str(kind): count for kind, count in counts.items()}
    return ListTableSchemaVersionsUseCaseOutput.Version(
        schema_id=schema.schema_id,
        previous_schema_id=None if previous is None else previous.schema_id,
        current=schema.schema_id == table.current_schema_id,
        column_count=len(schema.fields),
        changes=changes,
    )


class ListTableSchemaVersionsService(ListTableSchemaVersionsUseCase):
    """List every schema version of a table with what each changed against the version below it."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: ListTableSchemaVersionsUseCaseInput) -> ListTableSchemaVersionsUseCaseOutput:
        """Return the versions newest id first, or raise NotFoundError for an unknown table."""
        table = load_table(self._tables_repo, table_id_from_parts(request.catalog, request.namespace, request.name))
        return ListTableSchemaVersionsUseCaseOutput(
            current_schema_id=table.current_schema_id,
            items=tuple(_version(table, schema) for schema in reversed(table.schemas)),
        )
