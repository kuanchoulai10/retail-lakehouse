"""Define the RemoveOrphanFilesPolicy alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.operation_policy import OperationPolicy
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_execution_policy import (  # noqa: E501
    RemoveOrphanFilesExecutionPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.remove_orphan_files_trigger_policy import (  # noqa: E501
    RemoveOrphanFilesTriggerPolicy,
)

RemoveOrphanFilesPolicy = OperationPolicy[RemoveOrphanFilesTriggerPolicy, RemoveOrphanFilesExecutionPolicy]
