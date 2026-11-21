"""Inbound ports for the table_discovery_policy group."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_discovery_policy.ensure_default_table_discovery_policy import (  # noqa: E501
    EnsureDefaultTableDiscoveryPolicyUseCase,
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
    EnsureDefaultTableDiscoveryPolicyUseCaseOutput,
)

__all__ = [
    "EnsureDefaultTableDiscoveryPolicyUseCase",
    "EnsureDefaultTableDiscoveryPolicyUseCaseInput",
    "EnsureDefaultTableDiscoveryPolicyUseCaseOutput",
]
