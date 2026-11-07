"""Define the GetTableMetadataUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table.get_table_metadata.input import (
    GetTableMetadataUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.get_table_metadata.output import (
    GetTableMetadataUseCaseOutput,
)
from base import UseCase


class GetTableMetadataUseCase(UseCase[GetTableMetadataUseCaseInput, GetTableMetadataUseCaseOutput]):
    """Get the catalog metadata of one table."""

    @abstractmethod
    def execute(self, request: GetTableMetadataUseCaseInput) -> GetTableMetadataUseCaseOutput:
        """Get the catalog metadata of one table."""
