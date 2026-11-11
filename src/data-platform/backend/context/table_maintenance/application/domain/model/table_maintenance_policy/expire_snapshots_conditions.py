"""Define the ExpireSnapshotsConditions value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.at_least import AtLeast


class ExpireSnapshotsConditions(ValueObject):
    """Conditions that make snapshot expiry worth running; a missing condition is not checked."""

    expirable_snapshots: AtLeast | None = None

    def is_empty(self) -> bool:
        """Return whether no condition is set."""
        return self.expirable_snapshots is None
