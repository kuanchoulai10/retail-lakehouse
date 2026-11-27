"""Define the AttachTableDiscoveryPolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.attach_table_discovery_policy.input import (  # noqa: E501
    AttachTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.attach_table_discovery_policy.output import (  # noqa: E501
    AttachTableDiscoveryPolicyUseCaseOutput,
)


class AttachTableDiscoveryPolicyUseCase(
    UseCase[AttachTableDiscoveryPolicyUseCaseInput, AttachTableDiscoveryPolicyUseCaseOutput]
):
    """Attach a discovery policy to a catalog, namespace or table."""

    @abstractmethod
    def execute(self, request: AttachTableDiscoveryPolicyUseCaseInput) -> AttachTableDiscoveryPolicyUseCaseOutput:
        """Attach a discovery policy to a catalog, namespace or table."""
