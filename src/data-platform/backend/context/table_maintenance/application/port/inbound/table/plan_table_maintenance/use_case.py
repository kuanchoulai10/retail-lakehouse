"""Define the PlanTableMaintenanceUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from context.table_maintenance.application.port.inbound.table.plan_table_maintenance.input import (
    PlanTableMaintenanceUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table.plan_table_maintenance.output import (
    PlanTableMaintenanceUseCaseOutput,
)
from base import UseCase


class PlanTableMaintenanceUseCase(UseCase[PlanTableMaintenanceUseCaseInput, PlanTableMaintenanceUseCaseOutput]):
    """Plan the maintenance operations of a table."""

    @abstractmethod
    def execute(self, request: PlanTableMaintenanceUseCaseInput) -> PlanTableMaintenanceUseCaseOutput:
        """Plan the maintenance operations of a table."""
