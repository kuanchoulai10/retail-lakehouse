"""Define the SyncDiscoverySchedulesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.sync_discovery_schedules.input import (  # noqa: E501
    SyncDiscoverySchedulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.sync_discovery_schedules.output import (  # noqa: E501
    SyncDiscoverySchedulesUseCaseOutput,
)


class SyncDiscoverySchedulesUseCase(UseCase[SyncDiscoverySchedulesUseCaseInput, SyncDiscoverySchedulesUseCaseOutput]):
    """Give each scanned catalog its discovery schedule and retire the schedules of the others."""

    @abstractmethod
    def execute(self, request: SyncDiscoverySchedulesUseCaseInput) -> SyncDiscoverySchedulesUseCaseOutput:
        """Give each scanned catalog its discovery schedule and retire the schedules of the others."""
