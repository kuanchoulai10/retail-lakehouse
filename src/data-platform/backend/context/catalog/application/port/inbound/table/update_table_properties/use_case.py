"""Define the UpdateTablePropertiesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.catalog.application.port.inbound.table.update_table_properties.input import (
    UpdateTablePropertiesUseCaseInput,
)
from context.catalog.application.port.inbound.table.update_table_properties.output import (
    UpdateTablePropertiesUseCaseOutput,
)


class UpdateTablePropertiesUseCase(UseCase[UpdateTablePropertiesUseCaseInput, UpdateTablePropertiesUseCaseOutput]):
    """Set and remove properties of an Iceberg table, guarded by the uuid that was loaded."""

    @abstractmethod
    def execute(self, request: UpdateTablePropertiesUseCaseInput) -> UpdateTablePropertiesUseCaseOutput:
        """Set and remove properties of an Iceberg table, guarded by the uuid that was loaded."""
