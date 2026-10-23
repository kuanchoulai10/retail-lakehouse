"""Define the TableReconcileWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableReconcileWorkflowInput:
    """Identify the table a reconcile workflow manages."""

    table_uuid: str
