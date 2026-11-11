"""Define the RewriteDataFilesPolicy value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.compaction_scope import CompactionScope
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_execution_policy import (  # noqa: E501
    RewriteDataFilesExecutionPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_data_files_trigger_policy import (  # noqa: E501
    RewriteDataFilesTriggerPolicy,
)


class RewriteDataFilesPolicy(ValueObject):
    """Say whether compaction is enabled, over which scope, when it is due and how it runs."""

    enabled: bool
    scope: CompactionScope
    trigger_policy: RewriteDataFilesTriggerPolicy
    execution_policy: RewriteDataFilesExecutionPolicy
