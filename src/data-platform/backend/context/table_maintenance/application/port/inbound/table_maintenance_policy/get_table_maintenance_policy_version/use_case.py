"""Define the GetTableMaintenancePolicyVersionUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.get_table_maintenance_policy_version.input import (  # noqa: E501
    GetTableMaintenancePolicyVersionUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.get_table_maintenance_policy_version.output import (  # noqa: E501
    GetTableMaintenancePolicyVersionUseCaseOutput,
)


class GetTableMaintenancePolicyVersionUseCase(
    UseCase[GetTableMaintenancePolicyVersionUseCaseInput, GetTableMaintenancePolicyVersionUseCaseOutput]
):
    """Get one version of a table maintenance policy."""

    @abstractmethod
    def execute(
        self, request: GetTableMaintenancePolicyVersionUseCaseInput
    ) -> GetTableMaintenancePolicyVersionUseCaseOutput:
        """Get one version of a table maintenance policy."""
