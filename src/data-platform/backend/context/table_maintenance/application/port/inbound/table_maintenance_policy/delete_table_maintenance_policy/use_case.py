"""Define the DeleteTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.delete_table_maintenance_policy.input import (  # noqa: E501
    DeleteTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.delete_table_maintenance_policy.output import (  # noqa: E501
    DeleteTableMaintenancePolicyUseCaseOutput,
)


class DeleteTableMaintenancePolicyUseCase(
    UseCase[DeleteTableMaintenancePolicyUseCaseInput, DeleteTableMaintenancePolicyUseCaseOutput]
):
    """Delete a table maintenance policy and its versions."""

    @abstractmethod
    def execute(self, request: DeleteTableMaintenancePolicyUseCaseInput) -> DeleteTableMaintenancePolicyUseCaseOutput:
        """Delete a table maintenance policy and its versions."""
