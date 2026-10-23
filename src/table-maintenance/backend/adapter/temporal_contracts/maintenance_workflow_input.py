"""Define the MaintenanceWorkflowInput workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaintenanceWorkflowInput:
    """Carry the planned operations of one maintenance run."""

    run_id: str
    table_uuid: str
    trigger: str
    operations: list[dict]
