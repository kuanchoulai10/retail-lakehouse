"""Define the EnsureDefaultTableDiscoveryPolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_discovery_policy.ensure_default_table_discovery_policy.input import (  # noqa: E501
    EnsureDefaultTableDiscoveryPolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_discovery_policy.ensure_default_table_discovery_policy.output import (  # noqa: E501
    EnsureDefaultTableDiscoveryPolicyUseCaseOutput,
)


class EnsureDefaultTableDiscoveryPolicyUseCase(
    UseCase[EnsureDefaultTableDiscoveryPolicyUseCaseInput, EnsureDefaultTableDiscoveryPolicyUseCaseOutput]
):
    """Create the default table discovery policy when it is missing."""

    @abstractmethod
    def execute(
        self, request: EnsureDefaultTableDiscoveryPolicyUseCaseInput
    ) -> EnsureDefaultTableDiscoveryPolicyUseCaseOutput:
        """Create the default table discovery policy when it is missing."""
