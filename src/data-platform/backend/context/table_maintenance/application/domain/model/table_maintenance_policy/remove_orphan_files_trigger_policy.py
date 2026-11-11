"""Define the RemoveOrphanFilesTriggerPolicy alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_conditions import (
    RemoveOrphanFilesConditions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.trigger_policy import TriggerPolicy

RemoveOrphanFilesTriggerPolicy = TriggerPolicy[RemoveOrphanFilesConditions]
