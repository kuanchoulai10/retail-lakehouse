"""Define the DeleteTableDiscoveryPolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.delete_table_discovery_policy.input import (  # noqa: E501
    DeleteTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.delete_table_discovery_policy.output import (  # noqa: E501
    DeleteTableDiscoveryPolicyUseCaseOutput,
)


class DeleteTableDiscoveryPolicyUseCase(
    UseCase[DeleteTableDiscoveryPolicyUseCaseInput, DeleteTableDiscoveryPolicyUseCaseOutput]
):
    """Delete a discovery policy and its versions."""

    @abstractmethod
    def execute(self, request: DeleteTableDiscoveryPolicyUseCaseInput) -> DeleteTableDiscoveryPolicyUseCaseOutput:
        """Delete a discovery policy and its versions."""
