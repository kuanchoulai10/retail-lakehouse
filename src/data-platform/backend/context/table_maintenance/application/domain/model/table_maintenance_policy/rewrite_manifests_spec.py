"""Define the RewriteManifestsSpec alias."""

from __future__ import annotations

from context.table_maintenance.application.domain.model.table_maintenance_policy.operation_spec import (
    OperationSpec,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_options import (
    RewriteManifestsOptions,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy.rewrite_manifests_target import (
    RewriteManifestsTarget,
)

RewriteManifestsSpec = OperationSpec[RewriteManifestsTarget, RewriteManifestsOptions]
"""The ``rewrite_manifests`` block of a policy."""
