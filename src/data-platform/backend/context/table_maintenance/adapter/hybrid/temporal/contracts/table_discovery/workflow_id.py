"""Define the table_discovery_adhoc_workflow_id helper."""

from __future__ import annotations


def table_discovery_adhoc_workflow_id(catalog: str, namespace: str, *, change_id: str | None = None) -> str:
    """Return the workflow ID of an ad-hoc discovery run for one namespace of a catalog.

    A whole catalog is scanned under ``table_discovery_catalog_workflow_id`` instead. A run started
    by a change of the discovery policies is ``trigger=policy-changed`` with the change's id, so each
    change gets its own run instead of joining one that read older settings. Any other ad hoc run is
    ``trigger=adhoc``.
    """
    trigger = "trigger=adhoc" if change_id is None else f"trigger=policy-changed:change={change_id}"
    return f"table-discovery:catalog={catalog}:namespace={namespace}:{trigger}"
