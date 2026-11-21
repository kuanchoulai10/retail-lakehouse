"""Detach a discovery policy's attachment, named by its id."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.detach_table_discovery_policy.input import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.detach_table_discovery_policy.output import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy_attachment.detach_table_discovery_policy.use_case import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCase,
)

__all__ = [
    "DetachTableDiscoveryPolicyUseCase",
    "DetachTableDiscoveryPolicyUseCaseInput",
    "DetachTableDiscoveryPolicyUseCaseOutput",
]
