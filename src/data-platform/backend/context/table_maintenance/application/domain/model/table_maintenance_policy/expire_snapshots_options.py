"""Define the ExpireSnapshotsOptions value object."""

from __future__ import annotations

from typing import Any

from pydantic import PositiveInt, SerializerFunctionWrapHandler, model_serializer

from base import ValueObject


class ExpireSnapshotsOptions(ValueObject):
    """A curated subset of Iceberg's ``expire_snapshots`` arguments; an unset one is left to the procedure.

    The age and the number to keep belong to the target, so they are no options.
    """

    max_concurrent_deletes: PositiveInt | None = None
    stream_results: bool | None = None

    @model_serializer(mode="wrap")
    def _leave_unset_out(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Write only the options that are set, so an unset one stays left to the procedure."""
        return {key: value for key, value in handler(self).items() if value is not None}
