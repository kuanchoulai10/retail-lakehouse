"""Define the cooldowns a platform runs with unless it is told otherwise."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table.operation_cooldowns import (
    OperationCooldowns,
)

DEFAULT_OPERATION_COOLDOWNS = OperationCooldowns.platform_default()
