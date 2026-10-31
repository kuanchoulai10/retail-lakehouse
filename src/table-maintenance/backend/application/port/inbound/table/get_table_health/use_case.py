"""Define the GetTableHealthUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.table.get_table_health.input import (
    GetTableHealthUseCaseInput,
)
from application.port.inbound.table.get_table_health.output import (
    GetTableHealthUseCaseOutput,
)
from base import UseCase


class GetTableHealthUseCase(
    UseCase[GetTableHealthUseCaseInput, GetTableHealthUseCaseOutput]
):
    """Get the maintenance health of one table."""

    @abstractmethod
    def execute(
        self, request: GetTableHealthUseCaseInput
    ) -> GetTableHealthUseCaseOutput:
        """Get the maintenance health of one table."""
