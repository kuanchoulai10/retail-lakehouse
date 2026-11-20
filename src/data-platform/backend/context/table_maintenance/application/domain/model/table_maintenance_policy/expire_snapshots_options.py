"""Define the ExpireSnapshotsOptions value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject


class ExpireSnapshotsOptions(ValueObject):
    """A curated subset of Iceberg's ``expire_snapshots`` arguments; an unset one is left to the procedure.

    The age and the number to keep belong to the target, so they are no options.
    """

    max_concurrent_deletes: PositiveInt | None = None
    stream_results: bool | None = None

    def procedure_arguments(self) -> dict[str, int | bool]:
        """Return the procedure arguments that are set."""
        arguments: dict[str, int | bool] = {}
        if self.max_concurrent_deletes is not None:
            arguments["max_concurrent_deletes"] = self.max_concurrent_deletes
        if self.stream_results is not None:
            arguments["stream_results"] = self.stream_results
        return arguments
