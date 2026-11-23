"""The fields a maintenance workflow sends with every record request, for a run planned under the default."""

from __future__ import annotations

from typing import Any

from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    DEFAULT_POLICY_ID,
    DEFAULT_POLICY_NAME,
)

PLANNED_RECORD_FIELDS: dict[str, Any] = {
    "ended_by": "result",
    "still_running": False,
    "max_attempts": 3,
    "policy_id": DEFAULT_POLICY_ID.value,
    "policy_name": DEFAULT_POLICY_NAME,
    "policy_version": 1,
    "policy_target": None,
}
