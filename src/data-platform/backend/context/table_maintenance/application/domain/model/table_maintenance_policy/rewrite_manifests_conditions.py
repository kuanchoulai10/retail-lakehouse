"""Define the RewriteManifestsConditions value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.small_manifests_condition import (
    SmallManifestsCondition,
)


class RewriteManifestsConditions(ValueObject):
    """Conditions that make a manifest rewrite worth running; a missing condition is not checked."""

    small_manifests: SmallManifestsCondition | None = None

    def is_empty(self) -> bool:
        """Return whether no condition is set."""
        return self.small_manifests is None
