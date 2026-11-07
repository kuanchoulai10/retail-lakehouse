"""Inbound ports for the table group."""

from __future__ import annotations

from context.catalog.application.port.inbound.table.create_table.input import (
    CreateTableUseCaseInput,
    CreateTableUseCaseInputPartitionField,
    CreateTableUseCaseInputSchemaField,
)
from context.catalog.application.port.inbound.table.create_table.output import (
    CreateTableUseCaseOutput,
)
from context.catalog.application.port.inbound.table.create_table.use_case import (
    CreateTableUseCase,
)
from context.catalog.application.port.inbound.table.delete_table.input import (
    DeleteTableUseCaseInput,
)
from context.catalog.application.port.inbound.table.delete_table.output import (
    DeleteTableUseCaseOutput,
)
from context.catalog.application.port.inbound.table.delete_table.use_case import (
    DeleteTableUseCase,
)
from context.catalog.application.port.inbound.table.get_table.input import (
    GetTableUseCaseInput,
)
from context.catalog.application.port.inbound.table.get_table.output import (
    GetTableUseCaseOutput,
)
from context.catalog.application.port.inbound.table.get_table.use_case import (
    GetTableUseCase,
)
from context.catalog.application.port.inbound.table.list_tables.input import (
    ListTablesUseCaseInput,
)
from context.catalog.application.port.inbound.table.list_tables.output import (
    ListTablesUseCaseOutput,
    ListTablesUseCaseOutputItem,
)
from context.catalog.application.port.inbound.table.list_tables.use_case import (
    ListTablesUseCase,
)
from context.catalog.application.port.inbound.table.rename_table.input import (
    RenameTableUseCaseInput,
)
from context.catalog.application.port.inbound.table.rename_table.output import (
    RenameTableUseCaseOutput,
)
from context.catalog.application.port.inbound.table.rename_table.use_case import (
    RenameTableUseCase,
)
from context.catalog.application.port.inbound.table.update_table_properties.input import (
    UpdateTablePropertiesUseCaseInput,
)
from context.catalog.application.port.inbound.table.update_table_properties.output import (
    UpdateTablePropertiesUseCaseOutput,
)
from context.catalog.application.port.inbound.table.update_table_properties.use_case import (
    UpdateTablePropertiesUseCase,
)

__all__ = [
    "CreateTableUseCase",
    "CreateTableUseCaseInput",
    "CreateTableUseCaseInputPartitionField",
    "CreateTableUseCaseInputSchemaField",
    "CreateTableUseCaseOutput",
    "DeleteTableUseCase",
    "DeleteTableUseCaseInput",
    "DeleteTableUseCaseOutput",
    "GetTableUseCase",
    "GetTableUseCaseInput",
    "GetTableUseCaseOutput",
    "ListTablesUseCase",
    "ListTablesUseCaseInput",
    "ListTablesUseCaseOutput",
    "ListTablesUseCaseOutputItem",
    "RenameTableUseCase",
    "RenameTableUseCaseInput",
    "RenameTableUseCaseOutput",
    "UpdateTablePropertiesUseCase",
    "UpdateTablePropertiesUseCaseInput",
    "UpdateTablePropertiesUseCaseOutput",
]
