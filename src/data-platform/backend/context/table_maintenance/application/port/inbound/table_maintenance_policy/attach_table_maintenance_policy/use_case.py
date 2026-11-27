"""Define the AttachTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy.attach_table_maintenance_policy.input import (  # noqa: E501
    AttachTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.attach_table_maintenance_policy.output import (  # noqa: E501
    AttachTableMaintenancePolicyUseCaseOutput,
)


class AttachTableMaintenancePolicyUseCase(
    UseCase[AttachTableMaintenancePolicyUseCaseInput, AttachTableMaintenancePolicyUseCaseOutput]
):
    """Attach a maintenance policy to a catalog, namespace or table."""

    @abstractmethod
    def execute(self, request: AttachTableMaintenancePolicyUseCaseInput) -> AttachTableMaintenancePolicyUseCaseOutput:
        """Attach a maintenance policy to a catalog, namespace or table."""
