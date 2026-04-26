"""Define the GetTableUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.get_table.input import GetTableInput
from application.port.inbound.catalog.get_table.output import GetTableOutput


class GetTableUseCase(UseCase[GetTableInput, GetTableOutput]):
    """Get metadata for a specific table."""
