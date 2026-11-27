"""Define the ResolveApplicableTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.resolve_applicable_table_maintenance_policy.input import (  # noqa: E501
    ResolveApplicableTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.resolve_applicable_table_maintenance_policy.output import (  # noqa: E501
    ResolveApplicableTableMaintenancePolicyUseCaseOutput,
)


class ResolveApplicableTableMaintenancePolicyUseCase(
    UseCase[ResolveApplicableTableMaintenancePolicyUseCaseInput, ResolveApplicableTableMaintenancePolicyUseCaseOutput]
):
    """Resolve the maintenance policy that applies to a catalog, namespace or table."""

    @abstractmethod
    def execute(
        self, request: ResolveApplicableTableMaintenancePolicyUseCaseInput
    ) -> ResolveApplicableTableMaintenancePolicyUseCaseOutput:
        """Resolve the maintenance policy that applies to a catalog, namespace or table."""
