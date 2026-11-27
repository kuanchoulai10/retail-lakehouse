"""Give each scanned catalog its discovery schedule and retire the schedules of the others."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy.sync_discovery_schedules.input import (  # noqa: E501
    SyncDiscoverySchedulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.sync_discovery_schedules.output import (  # noqa: E501
    SyncDiscoverySchedulesUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.sync_discovery_schedules.use_case import (  # noqa: E501
    SyncDiscoverySchedulesUseCase,
)

__all__ = [
    "SyncDiscoverySchedulesUseCase",
    "SyncDiscoverySchedulesUseCaseInput",
    "SyncDiscoverySchedulesUseCaseOutput",
]
