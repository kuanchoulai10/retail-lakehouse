"""Define the RewriteDataFilesConditions value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.at_least import AtLeast


class RewriteDataFilesConditions(ValueObject):
    """Conditions that make compaction worth running; a missing condition is not checked."""

    reducible_files: AtLeast | None = None

    def is_empty(self) -> bool:
        """Return whether no condition is set."""
        return self.reducible_files is None
