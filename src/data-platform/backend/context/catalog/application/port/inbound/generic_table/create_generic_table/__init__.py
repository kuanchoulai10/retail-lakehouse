"""Create a generic table from the create generic table form."""

from context.catalog.application.port.inbound.generic_table.create_generic_table.input import (
    CreateGenericTableUseCaseInput,
)
from context.catalog.application.port.inbound.generic_table.create_generic_table.output import (
    CreateGenericTableUseCaseOutput,
)
from context.catalog.application.port.inbound.generic_table.create_generic_table.use_case import (
    CreateGenericTableUseCase,
)

__all__ = [
    "CreateGenericTableUseCase",
    "CreateGenericTableUseCaseInput",
    "CreateGenericTableUseCaseOutput",
]
