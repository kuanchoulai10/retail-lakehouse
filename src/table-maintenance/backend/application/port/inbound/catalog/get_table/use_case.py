"""Define the GetTableUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.get_table.input import GetTableUseCaseInput
from application.port.inbound.catalog.get_table.output import GetTableUseCaseOutput


class GetTableUseCase(UseCase[GetTableUseCaseInput, GetTableUseCaseOutput]):
    """Get metadata for a specific table."""
