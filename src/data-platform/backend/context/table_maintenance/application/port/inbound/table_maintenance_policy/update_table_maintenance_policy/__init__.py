"""Replace a table maintenance policy's content as a new version."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_maintenance_policy.update_table_maintenance_policy.input import (  # noqa: E501
    UpdateTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.update_table_maintenance_policy.output import (  # noqa: E501
    UpdateTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.update_table_maintenance_policy.use_case import (  # noqa: E501
    UpdateTableMaintenancePolicyUseCase,
)

__all__ = [
    "UpdateTableMaintenancePolicyUseCase",
    "UpdateTableMaintenancePolicyUseCaseInput",
    "UpdateTableMaintenancePolicyUseCaseOutput",
]
