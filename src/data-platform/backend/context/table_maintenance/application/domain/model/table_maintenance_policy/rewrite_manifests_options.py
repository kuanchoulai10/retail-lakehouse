"""Define the RewriteManifestsOptions value object."""

from __future__ import annotations

from base import ValueObject


class RewriteManifestsOptions(ValueObject):
    """A curated subset of Iceberg's ``rewrite_manifests`` arguments; an unset one is left to the procedure."""

    use_caching: bool | None = None

    def procedure_arguments(self) -> dict[str, bool]:
        """Return the procedure arguments that are set."""
        return {} if self.use_caching is None else {"use_caching": self.use_caching}
