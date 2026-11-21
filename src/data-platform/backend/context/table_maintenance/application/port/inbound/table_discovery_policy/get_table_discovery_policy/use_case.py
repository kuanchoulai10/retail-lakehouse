"""Define the GetTableDiscoveryPolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.get_table_discovery_policy.input import (  # noqa: E501
    GetTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.get_table_discovery_policy.output import (  # noqa: E501
    GetTableDiscoveryPolicyUseCaseOutput,
)


class GetTableDiscoveryPolicyUseCase(
    UseCase[GetTableDiscoveryPolicyUseCaseInput, GetTableDiscoveryPolicyUseCaseOutput]
):
    """Get the current version of a discovery policy."""

    @abstractmethod
    def execute(self, request: GetTableDiscoveryPolicyUseCaseInput) -> GetTableDiscoveryPolicyUseCaseOutput:
        """Get the current version of a discovery policy."""
