"""Attach a maintenance policy to a catalog, namespace or table."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_maintenance_policy.attach_table_maintenance_policy.input import (  # noqa: E501
    AttachTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.attach_table_maintenance_policy.output import (  # noqa: E501
    AttachTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy.attach_table_maintenance_policy.use_case import (  # noqa: E501
    AttachTableMaintenancePolicyUseCase,
)

__all__ = [
    "AttachTableMaintenancePolicyUseCase",
    "AttachTableMaintenancePolicyUseCaseInput",
    "AttachTableMaintenancePolicyUseCaseOutput",
]
