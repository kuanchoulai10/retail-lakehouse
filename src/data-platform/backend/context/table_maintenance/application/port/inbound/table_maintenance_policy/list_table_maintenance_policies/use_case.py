"""Define the ListTableMaintenancePoliciesUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.list_table_maintenance_policies.input import (  # noqa: E501
    ListTableMaintenancePoliciesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.list_table_maintenance_policies.output import (  # noqa: E501
    ListTableMaintenancePoliciesUseCaseOutput,
)


class ListTableMaintenancePoliciesUseCase(
    UseCase[ListTableMaintenancePoliciesUseCaseInput, ListTableMaintenancePoliciesUseCaseOutput]
):
    """List all table maintenance policies."""

    @abstractmethod
    def execute(self, request: ListTableMaintenancePoliciesUseCaseInput) -> ListTableMaintenancePoliciesUseCaseOutput:
        """List all table maintenance policies."""
