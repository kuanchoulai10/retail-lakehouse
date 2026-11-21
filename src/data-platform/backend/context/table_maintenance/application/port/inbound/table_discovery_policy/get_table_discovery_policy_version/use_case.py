"""Define the GetTableDiscoveryPolicyVersionUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.get_table_discovery_policy_version.input import (  # noqa: E501
    GetTableDiscoveryPolicyVersionUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.get_table_discovery_policy_version.output import (  # noqa: E501
    GetTableDiscoveryPolicyVersionUseCaseOutput,
)


class GetTableDiscoveryPolicyVersionUseCase(
    UseCase[GetTableDiscoveryPolicyVersionUseCaseInput, GetTableDiscoveryPolicyVersionUseCaseOutput]
):
    """Get one version of a discovery policy."""

    @abstractmethod
    def execute(
        self, request: GetTableDiscoveryPolicyVersionUseCaseInput
    ) -> GetTableDiscoveryPolicyVersionUseCaseOutput:
        """Get one version of a discovery policy."""
