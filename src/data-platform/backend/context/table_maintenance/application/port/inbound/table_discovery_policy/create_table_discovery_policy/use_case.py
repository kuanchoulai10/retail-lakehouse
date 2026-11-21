"""Define the CreateTableDiscoveryPolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.create_table_discovery_policy.input import (  # noqa: E501
    CreateTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.create_table_discovery_policy.output import (  # noqa: E501
    CreateTableDiscoveryPolicyUseCaseOutput,
)


class CreateTableDiscoveryPolicyUseCase(
    UseCase[CreateTableDiscoveryPolicyUseCaseInput, CreateTableDiscoveryPolicyUseCaseOutput]
):
    """Create a discovery policy at version 1."""

    @abstractmethod
    def execute(self, request: CreateTableDiscoveryPolicyUseCaseInput) -> CreateTableDiscoveryPolicyUseCaseOutput:
        """Create a discovery policy at version 1."""
