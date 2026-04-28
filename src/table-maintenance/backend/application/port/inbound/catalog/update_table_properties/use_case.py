"""Define the UpdateTablePropertiesUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesInput,
)
from application.port.inbound.catalog.update_table_properties.output import (
    UpdateTablePropertiesOutput,
)


class UpdateTablePropertiesUseCase(
    UseCase[UpdateTablePropertiesInput, UpdateTablePropertiesOutput]
):
    """Update properties for a specific table."""
