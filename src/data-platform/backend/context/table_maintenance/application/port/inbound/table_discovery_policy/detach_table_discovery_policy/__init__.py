"""Detach a discovery policy from the catalog, namespace or table that holds it."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy.detach_table_discovery_policy.input import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.detach_table_discovery_policy.output import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.detach_table_discovery_policy.use_case import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCase,
)

__all__ = [
    "DetachTableDiscoveryPolicyUseCase",
    "DetachTableDiscoveryPolicyUseCaseInput",
    "DetachTableDiscoveryPolicyUseCaseOutput",
]
