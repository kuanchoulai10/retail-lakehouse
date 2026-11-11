"""Define the table_discovery_adhoc_workflow_id helper."""

from __future__ import annotations


def table_discovery_adhoc_workflow_id(catalog: str, namespace: str | None, *, rules_version: int | None = None) -> str:
    """Return the workflow ID of an ad-hoc discovery run for a catalog or namespace.

    The ``trigger`` segment keeps it distinct from the scheduled runs. A run
    started by a save of the discovery rules is ``trigger=rules-saved`` with the
    saved version, so each save gets its own run instead of joining one that
    read older rules; any other ad hoc run is ``trigger=adhoc``.
    """
    scope = f"catalog={catalog}" if namespace is None else (f"catalog={catalog}:namespace={namespace}")
    trigger = "trigger=adhoc" if rules_version is None else f"trigger=rules-saved:version={rules_version}"
    return f"table-discovery:{scope}:{trigger}"
