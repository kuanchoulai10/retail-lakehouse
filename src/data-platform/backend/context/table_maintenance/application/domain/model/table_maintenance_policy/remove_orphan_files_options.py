"""Define the RemoveOrphanFilesOptions value object."""

from __future__ import annotations

from typing import Any

from pydantic import PositiveInt, SerializerFunctionWrapHandler, model_serializer

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

    @model_serializer(mode="wrap")
    def _leave_unset_out(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Write only the options that are set, so an unset one stays left to the procedure."""
        return {key: value for key, value in handler(self).items() if value is not None}

    def procedure_arguments(self) -> dict[str, int | str]:
        """Return the procedure arguments that are set."""
        arguments: dict[str, int | str] = {}
        if self.max_concurrent_deletes is not None:
            arguments["max_concurrent_deletes"] = self.max_concurrent_deletes
        if self.prefix_mismatch_mode is not None:
            arguments["prefix_mismatch_mode"] = str(self.prefix_mismatch_mode)
        return arguments
