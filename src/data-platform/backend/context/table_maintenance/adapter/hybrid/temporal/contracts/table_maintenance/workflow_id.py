"""Define the table_maintenance_workflow_id helper."""

from __future__ import annotations


def table_maintenance_workflow_id(table_uuid: str) -> str:
    """Return the workflow ID every maintenance run of a table runs under.

    A table runs one maintenance workflow at a time: the reconciliation starts
    each run under this ID, so a start while another run of the table is still
    running is refused, and a run that closed frees the ID for the next one.
    The table uuid never changes, so a rename keeps the ID.
    """
    return f"table-maintenance:table-uuid={table_uuid}"
