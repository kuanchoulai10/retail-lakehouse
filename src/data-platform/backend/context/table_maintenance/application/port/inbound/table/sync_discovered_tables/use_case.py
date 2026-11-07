"""Define the SyncDiscoveredTablesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table.sync_discovered_tables.input import (
    SyncDiscoveredTablesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.sync_discovered_tables.output import (
    SyncDiscoveredTablesUseCaseOutput,
)
from base import UseCase


class SyncDiscoveredTablesUseCase(
    UseCase[SyncDiscoveredTablesUseCaseInput, SyncDiscoveredTablesUseCaseOutput]
):
    """Synchronise the registry with the tables found in the catalog."""

    @abstractmethod
    def execute(
        self, request: SyncDiscoveredTablesUseCaseInput
    ) -> SyncDiscoveredTablesUseCaseOutput:
        """Synchronise the registry with the tables found in the catalog."""
