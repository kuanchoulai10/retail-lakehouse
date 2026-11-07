"""Get one generic table with its format, base location, doc and properties."""

from context.catalog.application.port.inbound.generic_table.get_generic_table.input import (
    GetGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.get_generic_table.output import (
    GetGenericTableUseCaseOutput,
)
from context.catalog.application.port.inbound.generic_table.get_generic_table.use_case import (
    GetGenericTableUseCase,
)

__all__ = [
    "GetGenericTableUseCase",
    "GetGenericTableUseCaseInput",
    "GetGenericTableUseCaseOutput",
]
