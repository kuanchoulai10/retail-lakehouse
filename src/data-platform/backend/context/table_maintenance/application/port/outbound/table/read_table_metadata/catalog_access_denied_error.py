"""Define the CatalogAccessDeniedError."""

from __future__ import annotations


class CatalogAccessDeniedError(Exception):
    """The catalog gateway may not read the named catalog: the server refuses the platform's credential.

    Raised instead of an empty listing or a missing table, so a caller can never mistake a catalog it
    cannot read for one that is empty or gone.
    """

    def __init__(self, catalog: str) -> None:
        """Remember the catalog name."""
        super().__init__(f"the platform's catalog credential cannot read catalog {catalog}")
        self.catalog = catalog
