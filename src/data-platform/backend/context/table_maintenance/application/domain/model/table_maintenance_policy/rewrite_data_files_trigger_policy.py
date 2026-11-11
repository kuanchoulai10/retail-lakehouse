"""Define the RewriteDataFilesTriggerPolicy alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_conditions import (
    RewriteDataFilesConditions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.trigger_policy import TriggerPolicy

RewriteDataFilesTriggerPolicy = TriggerPolicy[RewriteDataFilesConditions]
