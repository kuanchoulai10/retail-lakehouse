"""Define the RewriteManifestsPolicy alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.operation_policy import OperationPolicy
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_execution_policy import (  # noqa: E501
    RewriteManifestsExecutionPolicy,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_trigger_policy import (  # noqa: E501
    RewriteManifestsTriggerPolicy,
)

RewriteManifestsPolicy = OperationPolicy[RewriteManifestsTriggerPolicy, RewriteManifestsExecutionPolicy]
