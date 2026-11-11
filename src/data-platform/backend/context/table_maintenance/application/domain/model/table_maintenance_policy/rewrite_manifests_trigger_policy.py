"""Define the RewriteManifestsTriggerPolicy alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_conditions import (
    RewriteManifestsConditions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.trigger_policy import TriggerPolicy

RewriteManifestsTriggerPolicy = TriggerPolicy[RewriteManifestsConditions]
