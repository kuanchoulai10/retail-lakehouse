"""Define the UpdateTableDiscoveryPolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.update_table_discovery_policy.input import (  # noqa: E501
    UpdateTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.update_table_discovery_policy.output import (  # noqa: E501
    UpdateTableDiscoveryPolicyUseCaseOutput,
)


class UpdateTableDiscoveryPolicyUseCase(
    UseCase[UpdateTableDiscoveryPolicyUseCaseInput, UpdateTableDiscoveryPolicyUseCaseOutput]
):
    """Replace a discovery policy's content as a new version."""

    @abstractmethod
    def execute(self, request: UpdateTableDiscoveryPolicyUseCaseInput) -> UpdateTableDiscoveryPolicyUseCaseOutput:
        """Replace a discovery policy's content as a new version."""
