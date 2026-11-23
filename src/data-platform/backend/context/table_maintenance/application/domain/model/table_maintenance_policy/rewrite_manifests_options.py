"""Define the RewriteManifestsOptions value object."""

from __future__ import annotations

from typing import Any

from pydantic import SerializerFunctionWrapHandler, model_serializer

from base import ValueObject


class RewriteManifestsOptions(ValueObject):
    """A curated subset of Iceberg's ``rewrite_manifests`` arguments; an unset one is left to the procedure."""

    use_caching: bool | None = None

    @model_serializer(mode="wrap")
    def _leave_unset_out(self, handler: SerializerFunctionWrapHandler) -> dict[str, Any]:
        """Write only the options that are set, so an unset one stays left to the procedure."""
        return {key: value for key, value in handler(self).items() if value is not None}
