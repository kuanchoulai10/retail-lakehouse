"""Define the CatalogUnavailableError exception."""

from __future__ import annotations


class CatalogUnavailableError(Exception):
    """Signal that the catalog service could not be reached or failed."""
