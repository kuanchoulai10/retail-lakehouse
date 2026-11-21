"""Define the GetEffectivePoliciesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table.get_effective_policies.input import (
    GetEffectivePoliciesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.get_effective_policies.output import (
    GetEffectivePoliciesUseCaseOutput,
)


class GetEffectivePoliciesUseCase(UseCase[GetEffectivePoliciesUseCaseInput, GetEffectivePoliciesUseCaseOutput]):
    """Get the policy of each kind that applies to a table or a place in the catalog."""

    @abstractmethod
    def execute(self, request: GetEffectivePoliciesUseCaseInput) -> GetEffectivePoliciesUseCaseOutput:
        """Get the policy of each kind that applies to a table or a place in the catalog."""
