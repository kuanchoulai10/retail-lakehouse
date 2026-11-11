"""Define the UpdateTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.update_table_maintenance_policy.input import (  # noqa: E501
    UpdateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.update_table_maintenance_policy.output import (  # noqa: E501
    UpdateTableMaintenancePolicyUseCaseOutput,
)


class UpdateTableMaintenancePolicyUseCase(
    UseCase[UpdateTableMaintenancePolicyUseCaseInput, UpdateTableMaintenancePolicyUseCaseOutput]
):
    """Replace a table maintenance policy's content as a new version."""

    @abstractmethod
    def execute(self, request: UpdateTableMaintenancePolicyUseCaseInput) -> UpdateTableMaintenancePolicyUseCaseOutput:
        """Replace a table maintenance policy's content as a new version."""
