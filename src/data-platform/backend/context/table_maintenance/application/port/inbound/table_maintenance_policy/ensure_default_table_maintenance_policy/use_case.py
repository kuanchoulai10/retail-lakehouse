"""Define the EnsureDefaultTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.ensure_default_table_maintenance_policy.input import (  # noqa: E501
    EnsureDefaultTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.ensure_default_table_maintenance_policy.output import (  # noqa: E501
    EnsureDefaultTableMaintenancePolicyUseCaseOutput,
)


class EnsureDefaultTableMaintenancePolicyUseCase(
    UseCase[EnsureDefaultTableMaintenancePolicyUseCaseInput, EnsureDefaultTableMaintenancePolicyUseCaseOutput]
):
    """Create the default table maintenance policy when it is missing."""

    @abstractmethod
    def execute(
        self, request: EnsureDefaultTableMaintenancePolicyUseCaseInput
    ) -> EnsureDefaultTableMaintenancePolicyUseCaseOutput:
        """Create the default table maintenance policy when it is missing."""
