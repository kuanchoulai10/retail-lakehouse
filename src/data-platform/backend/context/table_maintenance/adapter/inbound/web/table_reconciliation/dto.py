"""Define the table reconciliation API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReconciliationMeasurementApiResponse(BaseModel):
    """Describe one measurement; threshold, comparison and met are null for context."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    observed: int
    unit: str
    threshold: int | None
    comparison: str | None
    met: bool | None


class ReconciliationOperationApiResponse(BaseModel):
    """Describe what a reconciliation measured and decided for one operation."""

    model_config = ConfigDict(from_attributes=True)

    operation: str
    result: str
    combine: str
    measurements: list[ReconciliationMeasurementApiResponse]
    next_eligible_at: datetime | None


class TableReconciliationApiResponse(BaseModel):
    """Describe one reconciliation of a table."""

    model_config = ConfigDict(from_attributes=True)

    reconciliation_id: str
    table_uuid: str
    reconciled_at: datetime
    wake_reasons: dict[str, int]
    dry_run: bool
    outcome: str
    skip_reason: str | None
    operations: list[ReconciliationOperationApiResponse]
    run_id: str | None
