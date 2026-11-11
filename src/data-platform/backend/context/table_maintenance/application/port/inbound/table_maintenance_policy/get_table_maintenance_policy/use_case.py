"""Define the GetTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.get_table_maintenance_policy.input import (  # noqa: E501
    GetTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.get_table_maintenance_policy.output import (  # noqa: E501
    GetTableMaintenancePolicyUseCaseOutput,
)


class GetTableMaintenancePolicyUseCase(
    UseCase[GetTableMaintenancePolicyUseCaseInput, GetTableMaintenancePolicyUseCaseOutput]
):
    """Get the current version of a table maintenance policy."""

    @abstractmethod
    def execute(self, request: GetTableMaintenancePolicyUseCaseInput) -> GetTableMaintenancePolicyUseCaseOutput:
        """Get the current version of a table maintenance policy."""
