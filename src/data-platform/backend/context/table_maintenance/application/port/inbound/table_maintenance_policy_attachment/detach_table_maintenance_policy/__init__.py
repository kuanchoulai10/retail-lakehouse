"""Detach one of a maintenance policy's attachments, named by its ``pa-`` id."""

from __future__ import annotations

from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment.detach_table_maintenance_policy.input import (  # noqa: E501
    DetachTableMaintenancePolicyUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment.detach_table_maintenance_policy.output import (  # noqa: E501
    DetachTableMaintenancePolicyUseCaseOutput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy_attachment.detach_table_maintenance_policy.use_case import (  # noqa: E501
    DetachTableMaintenancePolicyUseCase,
)

__all__ = [
    "DetachTableMaintenancePolicyUseCase",
    "DetachTableMaintenancePolicyUseCaseInput",
    "DetachTableMaintenancePolicyUseCaseOutput",
]
