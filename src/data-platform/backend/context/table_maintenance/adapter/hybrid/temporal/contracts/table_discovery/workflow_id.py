"""Define the table_discovery_adhoc_workflow_id helper."""

from __future__ import annotations


def table_discovery_adhoc_workflow_id(catalog: str, namespace: str | None, *, change_id: str | None = None) -> str:
    """Return the workflow ID of an ad-hoc discovery run for a catalog or namespace.

    The ``trigger`` segment keeps it distinct from the scheduled runs. A run started by a change of
    the discovery policies is ``trigger=policy-changed`` with the change's id, so each change gets its
    own run instead of joining one that read older settings; any other ad hoc run is ``trigger=adhoc``.
    """
    scope = f"catalog={catalog}" if namespace is None else (f"catalog={catalog}:namespace={namespace}")
    trigger = "trigger=adhoc" if change_id is None else f"trigger=policy-changed:change={change_id}"
    return f"table-discovery:{scope}:{trigger}"
