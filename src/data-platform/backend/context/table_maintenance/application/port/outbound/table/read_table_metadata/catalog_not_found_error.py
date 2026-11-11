"""Define the CatalogNotFoundError."""

from __future__ import annotations


class CatalogNotFoundError(Exception):
    """The catalog gateway cannot open the named catalog because the server does not know it.

    Raised instead of an empty listing, so a caller can never mistake an unknown catalog for a
    catalog whose tables have all vanished.
    """

    def __init__(self, catalog: str) -> None:
        """Remember the catalog name."""
        super().__init__(f"catalog {catalog} not found")
        self.catalog = catalog
