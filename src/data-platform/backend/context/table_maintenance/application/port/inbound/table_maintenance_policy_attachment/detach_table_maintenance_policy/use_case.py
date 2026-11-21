"""Define the DetachTableMaintenancePolicyUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment.detach_table_maintenance_policy.input import (  # noqa: E501
    DetachTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment.detach_table_maintenance_policy.output import (  # noqa: E501
    DetachTableMaintenancePolicyUseCaseOutput,
)


class DetachTableMaintenancePolicyUseCase(
    UseCase[DetachTableMaintenancePolicyUseCaseInput, DetachTableMaintenancePolicyUseCaseOutput]
):
    """Detach one of a maintenance policy's attachments, named by its ``pa-`` id."""

    @abstractmethod
    def execute(self, request: DetachTableMaintenancePolicyUseCaseInput) -> DetachTableMaintenancePolicyUseCaseOutput:
        """Detach one of a maintenance policy's attachments, named by its ``pa-`` id."""
