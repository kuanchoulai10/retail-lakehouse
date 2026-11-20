"""Define the RemoveOrphanFilesOptions value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.prefix_mismatch_mode import (
    PrefixMismatchMode,
)


class RemoveOrphanFilesOptions(ValueObject):
    """A curated subset of Iceberg's ``remove_orphan_files`` arguments; an unset one is left to the procedure.

    The age belongs to the target, and a dry run and the location are the platform's, so they are no options.
    """

    max_concurrent_deletes: PositiveInt | None = None
    prefix_mismatch_mode: PrefixMismatchMode | None = None

    def procedure_arguments(self) -> dict[str, int | str]:
        """Return the procedure arguments that are set."""
        arguments: dict[str, int | str] = {}
        if self.max_concurrent_deletes is not None:
            arguments["max_concurrent_deletes"] = self.max_concurrent_deletes
        if self.prefix_mismatch_mode is not None:
            arguments["prefix_mismatch_mode"] = str(self.prefix_mismatch_mode)
        return arguments
