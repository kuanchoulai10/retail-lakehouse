"""Delete a table maintenance policy and its versions."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_maintenance_policy.delete_table_maintenance_policy.input import (  # noqa: E501
    DeleteTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.delete_table_maintenance_policy.output import (  # noqa: E501
    DeleteTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.delete_table_maintenance_policy.use_case import (  # noqa: E501
    DeleteTableMaintenancePolicyUseCase,
)

__all__ = [
    "DeleteTableMaintenancePolicyUseCase",
    "DeleteTableMaintenancePolicyUseCaseInput",
    "DeleteTableMaintenancePolicyUseCaseOutput",
]
