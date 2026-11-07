"""Inbound ports for the generic table group."""

from __future__ import annotations

from context.catalog.application.port.inbound.generic_table.create_generic_table.input import (
    CreateGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.create_generic_table.output import (
    CreateGenericTableUseCaseOutput,
)
from context.catalog.application.port.inbound.generic_table.create_generic_table.use_case import (
    CreateGenericTableUseCase,
)
from context.catalog.application.port.inbound.generic_table.delete_generic_table.input import (
    DeleteGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.delete_generic_table.output import (
    DeleteGenericTableUseCaseOutput,
)
from context.catalog.application.port.inbound.generic_table.delete_generic_table.use_case import (
    DeleteGenericTableUseCase,
)
from context.catalog.application.port.inbound.generic_table.get_generic_table.input import (
    GetGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.get_generic_table.output import (
    GetGenericTableUseCaseOutput,
)
from context.catalog.application.port.inbound.generic_table.get_generic_table.use_case import (
    GetGenericTableUseCase,
)
from context.catalog.application.port.inbound.generic_table.list_generic_tables.input import (
    ListGenericTablesUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.list_generic_tables.output import (
    ListGenericTablesUseCaseOutput,
    ListGenericTablesUseCaseOutputItem,
)
from context.catalog.application.port.inbound.generic_table.list_generic_tables.use_case import (
    ListGenericTablesUseCase,
)

__all__ = [
    "CreateGenericTableUseCase",
    "CreateGenericTableUseCaseInput",
    "CreateGenericTableUseCaseOutput",
    "DeleteGenericTableUseCase",
    "DeleteGenericTableUseCaseInput",
    "DeleteGenericTableUseCaseOutput",
    "GetGenericTableUseCase",
    "GetGenericTableUseCaseInput",
    "GetGenericTableUseCaseOutput",
    "ListGenericTablesUseCase",
    "ListGenericTablesUseCaseInput",
    "ListGenericTablesUseCaseOutput",
    "ListGenericTablesUseCaseOutputItem",
]
