"""Define the DetachTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.detach_table_maintenance_policy.input import (  # noqa: E501
    DetachTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.detach_table_maintenance_policy.output import (  # noqa: E501
    DetachTableMaintenancePolicyUseCaseOutput,
)


class DetachTableMaintenancePolicyUseCase(
    UseCase[DetachTableMaintenancePolicyUseCaseInput, DetachTableMaintenancePolicyUseCaseOutput]
):
    """Detach a maintenance policy from a catalog, namespace or table."""

    @abstractmethod
    def execute(self, request: DetachTableMaintenancePolicyUseCaseInput) -> DetachTableMaintenancePolicyUseCaseOutput:
        """Detach a maintenance policy from a catalog, namespace or table."""
