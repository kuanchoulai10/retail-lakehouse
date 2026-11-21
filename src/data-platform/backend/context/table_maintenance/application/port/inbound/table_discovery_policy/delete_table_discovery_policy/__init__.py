"""Delete a discovery policy and its versions."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy.delete_table_discovery_policy.input import (  # noqa: E501
    DeleteTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.delete_table_discovery_policy.output import (  # noqa: E501
    DeleteTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.delete_table_discovery_policy.use_case import (  # noqa: E501
    DeleteTableDiscoveryPolicyUseCase,
)

__all__ = [
    "DeleteTableDiscoveryPolicyUseCase",
    "DeleteTableDiscoveryPolicyUseCaseInput",
    "DeleteTableDiscoveryPolicyUseCaseOutput",
]
