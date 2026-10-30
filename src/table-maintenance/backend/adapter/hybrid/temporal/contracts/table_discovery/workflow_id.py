"""Define the table_discovery_adhoc_workflow_id helper."""

from __future__ import annotations


def table_discovery_adhoc_workflow_id(catalog: str, namespace: str | None) -> str:
    """Return the workflow ID of an ad-hoc discovery run for a catalog or namespace.

    The ``trigger=adhoc`` segment keeps it distinct from the scheduled runs.
    """
    scope = (
        f"catalog={catalog}"
        if namespace is None
        else (f"catalog={catalog}:namespace={namespace}")
    )
    return f"table-discovery:{scope}:trigger=adhoc"
