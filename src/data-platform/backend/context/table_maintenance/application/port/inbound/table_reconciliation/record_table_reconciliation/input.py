"""Define the RecordTableReconciliationUseCaseInput."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class RecordTableReconciliationUseCaseInput:
    """Carry one reconciliation pass to record, as plain values.

    ``checks`` holds the plan's check items as dicts (operation, verdict, combine,
    measurements, next_eligible_at), the shape they have after crossing a Temporal activity.
    """

    reconciliation_id: str
    table_uuid: str
    reconciled_at: datetime
    wake_reasons: dict[str, int]
    dry_run: bool
    status: str
    skip_reason: str | None
    checks: list[dict[str, Any]]
    run_id: str | None
    run_start_failed: bool
