"""Define the RewriteManifestsTarget value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.at_most import AtMost


class RewriteManifestsTarget(ValueObject):
    """The manifest target: small manifests stay at or under ``small_manifests``."""

    small_manifests: AtMost
