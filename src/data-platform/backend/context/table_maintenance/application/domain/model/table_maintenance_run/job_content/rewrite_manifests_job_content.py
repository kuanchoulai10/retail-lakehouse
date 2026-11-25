"""Define the RewriteManifestsJobContent value object."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_policy import RewriteManifestsOptions


class RewriteManifestsJobContent(ValueObject):
    """Describe what one manifest rewrite does: the policy's options, none when it sets none."""

    operation: Literal[MaintenanceOperation.REWRITE_MANIFESTS] = MaintenanceOperation.REWRITE_MANIFESTS
    options: RewriteManifestsOptions = Field(default_factory=RewriteManifestsOptions)
