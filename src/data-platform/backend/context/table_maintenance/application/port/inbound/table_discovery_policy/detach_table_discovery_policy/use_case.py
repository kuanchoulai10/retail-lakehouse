"""Define the DetachTableDiscoveryPolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.detach_table_discovery_policy.input import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.detach_table_discovery_policy.output import (  # noqa: E501
    DetachTableDiscoveryPolicyUseCaseOutput,
)


class DetachTableDiscoveryPolicyUseCase(
    UseCase[DetachTableDiscoveryPolicyUseCaseInput, DetachTableDiscoveryPolicyUseCaseOutput]
):
    """Detach a discovery policy from the catalog, namespace or table that holds it."""

    @abstractmethod
    def execute(self, request: DetachTableDiscoveryPolicyUseCaseInput) -> DetachTableDiscoveryPolicyUseCaseOutput:
        """Detach a discovery policy from the catalog, namespace or table that holds it."""
