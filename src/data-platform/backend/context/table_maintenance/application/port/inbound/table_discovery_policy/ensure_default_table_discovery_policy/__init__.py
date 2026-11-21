"""Create the default table discovery policy when it is missing."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy.ensure_default_table_discovery_policy.input import (  # noqa: E501
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.ensure_default_table_discovery_policy.output import (  # noqa: E501
    EnsureDefaultTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.ensure_default_table_discovery_policy.use_case import (  # noqa: E501
    EnsureDefaultTableDiscoveryPolicyUseCase,
)

__all__ = [
    "EnsureDefaultTableDiscoveryPolicyUseCase",
    "EnsureDefaultTableDiscoveryPolicyUseCaseInput",
    "EnsureDefaultTableDiscoveryPolicyUseCaseOutput",
]
