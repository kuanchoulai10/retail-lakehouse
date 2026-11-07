"""Define the CreateTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.inbound.table import (
    CreateTableUseCase,
    CreateTableUseCaseInput,
    CreateTableUseCaseOutput,
)
from context.catalog.application.port.outbound.table import Schema, SchemaField, Table
from context.catalog.application.service.table.partition_spec_from_request import (
    partition_spec_from_request,
)
from context.catalog.application.service.table.table_id_from_parts import table_id_from_parts
from context.catalog.application.service.table.table_output_fields import table_output_fields

if TYPE_CHECKING:
    from context.catalog.application.port.inbound.table import CreateTableUseCaseInputSchemaField
    from context.catalog.application.port.outbound.table import TablesRepo


def _schema(requested: list[CreateTableUseCaseInputSchemaField]) -> Schema:
    """Number the form's columns 1, 2, ... and refuse an empty, blank or duplicate one."""
    if not requested:
        raise ValidationError("a table needs at least one field")
    names = [field.name for field in requested]
    if any(not name.strip() for name in names):
        raise ValidationError("field names must not be blank")
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise ValidationError(f"duplicate field names: {', '.join(duplicates)}")
    blank_types = [field.name for field in requested if not field.type.strip()]
    if blank_types:
        raise ValidationError(f"fields need a type: {', '.join(blank_types)}")
    return Schema(
        schema_id=0,
        fields=tuple(
            SchemaField(id=index, name=field.name, type=field.type.strip(), required=field.required, doc=field.doc)
            for index, field in enumerate(requested, start=1)
        ),
    )


class CreateTableService(CreateTableUseCase):
    """Create an Iceberg table from the create table form; the catalog assigns its uuid."""

    def __init__(self, tables_repo: TablesRepo) -> None:
        """Bind the repo."""
        self._tables_repo = tables_repo

    def execute(self, request: CreateTableUseCaseInput) -> CreateTableUseCaseOutput:
        """Validate the form, create the table and return it as the catalog saved it."""
        table_id = table_id_from_parts(request.catalog, request.namespace, request.name)
        schema = _schema(request.schema_fields)
        location = request.location.strip() if request.location and request.location.strip() else None
        table = Table.define(
            id=table_id,
            schema=schema,
            partition_spec=partition_spec_from_request(schema, request.partition_fields),
            location=location,
            properties=request.properties,
        )
        return CreateTableUseCaseOutput(**table_output_fields(self._tables_repo.create(table)))
