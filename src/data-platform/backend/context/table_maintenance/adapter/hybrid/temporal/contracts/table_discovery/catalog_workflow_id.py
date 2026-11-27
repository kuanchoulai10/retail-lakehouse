"""Define the table_discovery_catalog_workflow_id helper."""

from __future__ import annotations


def table_discovery_catalog_workflow_id(catalog: str) -> str:
    """Return the one workflow ID a scan of a whole catalog runs under, whoever starts it.

    The round and a catalog-wide request share it, so a catalog is scanned by one run at a time.
    """
    return f"table-discovery:catalog={catalog}"
