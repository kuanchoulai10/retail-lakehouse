"""Define the ResetTablePropertiesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.reset_table_properties.input import (
    ResetTablePropertiesUseCaseInput,
)
from context.catalog.application.port.inbound.table.reset_table_properties.output import (
    ResetTablePropertiesUseCaseOutput,
)


class ResetTablePropertiesUseCase(UseCase[ResetTablePropertiesUseCaseInput, ResetTablePropertiesUseCaseOutput]):
    """Reset properties of an Iceberg table to their defaults, guarded by the uuid that was loaded."""

    @abstractmethod
    def execute(self, request: ResetTablePropertiesUseCaseInput) -> ResetTablePropertiesUseCaseOutput:
        """Reset properties of an Iceberg table to their defaults, guarded by the uuid that was loaded."""
