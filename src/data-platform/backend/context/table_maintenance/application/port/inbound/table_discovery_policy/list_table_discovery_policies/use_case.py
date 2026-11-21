"""Define the ListTableDiscoveryPoliciesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.list_table_discovery_policies.input import (  # noqa: E501
    ListTableDiscoveryPoliciesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.list_table_discovery_policies.output import (  # noqa: E501
    ListTableDiscoveryPoliciesUseCaseOutput,
)


class ListTableDiscoveryPoliciesUseCase(
    UseCase[ListTableDiscoveryPoliciesUseCaseInput, ListTableDiscoveryPoliciesUseCaseOutput]
):
    """List all discovery policies."""

    @abstractmethod
    def execute(self, request: ListTableDiscoveryPoliciesUseCaseInput) -> ListTableDiscoveryPoliciesUseCaseOutput:
        """List all discovery policies."""
