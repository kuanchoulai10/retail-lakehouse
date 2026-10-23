"""Define the SyncDiscoveredTablesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from application.port.inbound.discovery.sync_discovered_tables.input import (
    SyncDiscoveredTablesUseCaseInput,
)
from application.port.inbound.discovery.sync_discovered_tables.output import (
    SyncDiscoveredTablesUseCaseOutput,
)
from base.use_case import UseCase


class SyncDiscoveredTablesUseCase(
    UseCase[SyncDiscoveredTablesUseCaseInput, SyncDiscoveredTablesUseCaseOutput]
):
    """Synchronise the registry with the tables found in the catalog."""

    @abstractmethod
    def execute(
        self, request: SyncDiscoveredTablesUseCaseInput
    ) -> SyncDiscoveredTablesUseCaseOutput:
        """Synchronise the registry with the tables found in the catalog."""
