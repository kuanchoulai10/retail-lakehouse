"""Define the GetTableStorageUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table.get_table_storage.input import (
    GetTableStorageUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.get_table_storage.output import (
    GetTableStorageUseCaseOutput,
)
from base import UseCase


class GetTableStorageUseCase(UseCase[GetTableStorageUseCaseInput, GetTableStorageUseCaseOutput]):
    """Get the storage split and reclaimed space of one table."""

    @abstractmethod
    def execute(self, request: GetTableStorageUseCaseInput) -> GetTableStorageUseCaseOutput:
        """Get the storage split and reclaimed space of one table."""
