"""Rename an Iceberg table, or move it to another namespace of its catalog."""

from context.catalog.application.port.inbound.table.rename_table.input import (
    RenameTableUseCaseInput,
)
from context.catalog.application.port.inbound.table.rename_table.output import (
    RenameTableUseCaseOutput,
)
from context.catalog.application.port.inbound.table.rename_table.use_case import (
    RenameTableUseCase,
)

__all__ = [
    "RenameTableUseCase",
    "RenameTableUseCaseInput",
    "RenameTableUseCaseOutput",
]
