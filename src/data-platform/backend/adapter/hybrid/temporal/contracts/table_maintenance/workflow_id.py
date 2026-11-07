"""Define the table_maintenance_workflow_id helper."""

from __future__ import annotations


def table_maintenance_workflow_id(table: str, run_id: str) -> str:
    """Return the workflow ID of the table maintenance workflow for a run.

    ``table`` is the fully qualified ``catalog.namespace.table`` name as of the
    run start; a later rename does not change the ID, so paths that only know
    the run look the ID up on the maintenance run instead of rebuilding it.
    """
    return f"table-maintenance:table={table}:run={run_id}"
