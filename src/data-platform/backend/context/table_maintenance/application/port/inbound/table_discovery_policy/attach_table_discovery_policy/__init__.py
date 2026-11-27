"""Attach a discovery policy to a catalog, namespace or table."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy.attach_table_discovery_policy.input import (  # noqa: E501
    AttachTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.attach_table_discovery_policy.output import (  # noqa: E501
    AttachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.attach_table_discovery_policy.use_case import (  # noqa: E501
    AttachTableDiscoveryPolicyUseCase,
)

__all__ = [
    "AttachTableDiscoveryPolicyUseCase",
    "AttachTableDiscoveryPolicyUseCaseInput",
    "AttachTableDiscoveryPolicyUseCaseOutput",
]
