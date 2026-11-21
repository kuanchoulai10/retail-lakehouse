"""Replace a discovery policy's content as a new version."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy.update_table_discovery_policy.input import (  # noqa: E501
    UpdateTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.update_table_discovery_policy.output import (  # noqa: E501
    UpdateTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.update_table_discovery_policy.use_case import (  # noqa: E501
    UpdateTableDiscoveryPolicyUseCase,
)

__all__ = [
    "UpdateTableDiscoveryPolicyUseCase",
    "UpdateTableDiscoveryPolicyUseCaseInput",
    "UpdateTableDiscoveryPolicyUseCaseOutput",
]
