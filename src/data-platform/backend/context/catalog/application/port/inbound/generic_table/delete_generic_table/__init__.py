"""Drop a generic table from the catalog."""

from context.catalog.application.port.inbound.generic_table.delete_generic_table.input import (
    DeleteGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.delete_generic_table.output import (
    DeleteGenericTableUseCaseOutput,
)
from context.catalog.application.port.inbound.generic_table.delete_generic_table.use_case import (
    DeleteGenericTableUseCase,
)

__all__ = [
    "DeleteGenericTableUseCase",
    "DeleteGenericTableUseCaseInput",
    "DeleteGenericTableUseCaseOutput",
]
