"""Define the UpdateTablePropertiesUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesUseCaseInput,
)
from application.port.inbound.catalog.update_table_properties.output import (
    UpdateTablePropertiesUseCaseOutput,
)


class UpdateTablePropertiesUseCase(
    UseCase[UpdateTablePropertiesUseCaseInput, UpdateTablePropertiesUseCaseOutput]
):
    """Update properties for a specific table."""
