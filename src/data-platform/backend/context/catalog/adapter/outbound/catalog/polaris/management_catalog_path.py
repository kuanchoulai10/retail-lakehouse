"""Define the management_catalog_path function."""

from __future__ import annotations

from urllib.parse import quote


def management_catalog_path(name: str) -> str:
    """Return the management API path of the catalog ``name``, encoded as one path segment."""
    return f"/catalogs/{quote(name, safe='')}"
