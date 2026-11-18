"""Define the RecordTableReconciliationUseCaseInput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseInput


class RecordTableReconciliationUseCaseInput(UseCaseInput):
    """Carry one reconciliation pass to record, as plain values.

    ``checks`` holds the plan's check items as dicts (operation, verdict,
    measurements, next_eligible_at), the shape they have after crossing a Temporal activity.
    ``policy_target`` is the plan's target dict (type, path and, for a table, table_uuid) or None.
    """

    reconciliation_id: str
    table_uuid: str
    reconciled_at: datetime
    wake_reasons: dict[str, int]
    dry_run: bool
    status: str
    skip_reason: str | None
    checks: tuple[dict[str, Any], ...]
    run_id: str | None
    run_start_failed: bool
    policy_name: str
    policy_version: int
    policy_target: dict[str, Any] | None
