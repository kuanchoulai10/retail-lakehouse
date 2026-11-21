"""Define the table_discovery_adhoc_workflow_id helper."""

from __future__ import annotations


def table_discovery_adhoc_workflow_id(
    catalog: str, namespace: str | None, *, change_id: str | None = None, retires_schedule: bool = False
) -> str:
    """Return the workflow ID of an ad-hoc discovery run for a catalog or namespace.

    The ``trigger`` segment keeps it distinct from the scheduled runs. A run started by a change of
    the discovery policies is ``trigger=policy-changed`` with the change's id, so each change gets its
    own run instead of joining one that read older settings. The final scan the worker start gives a
    catalog whose schedule it retires is ``trigger=schedule-retired`` with its own change id. Any
    other ad hoc run is ``trigger=adhoc``.
    """
    scope = f"catalog={catalog}" if namespace is None else (f"catalog={catalog}:namespace={namespace}")
    if change_id is None:
        trigger = "trigger=adhoc"
    else:
        kind = "schedule-retired" if retires_schedule else "policy-changed"
        trigger = f"trigger={kind}:change={change_id}"
    return f"table-discovery:{scope}:{trigger}"
