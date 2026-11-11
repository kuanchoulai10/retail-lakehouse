"""Define the CreateTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.create_table_maintenance_policy.input import (  # noqa: E501
    CreateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.create_table_maintenance_policy.output import (  # noqa: E501
    CreateTableMaintenancePolicyUseCaseOutput,
)


class CreateTableMaintenancePolicyUseCase(
    UseCase[CreateTableMaintenancePolicyUseCaseInput, CreateTableMaintenancePolicyUseCaseOutput]
):
    """Create a table maintenance policy at version 1."""

    @abstractmethod
    def execute(self, request: CreateTableMaintenancePolicyUseCaseInput) -> CreateTableMaintenancePolicyUseCaseOutput:
        """Create a table maintenance policy at version 1."""
