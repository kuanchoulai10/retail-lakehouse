"""Define the table_reconciliation_workflow_id helper."""

from __future__ import annotations


def table_reconciliation_workflow_id(table_uuid: str) -> str:
    """Return the workflow ID of the reconciliation workflow for a table."""
    return f"table-reconciliation:table-uuid={table_uuid}"
