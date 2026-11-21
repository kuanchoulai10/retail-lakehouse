"""Define the table reconciliation API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    measurements: list[ReconciliationMeasurementApiResponse]
    next_eligible_at: datetime | None
    run_id: str | None = Field(
        description="The mr- id of the maintenance run this operation started; set only when result is started."
    )


class ReconciliationPolicyTargetApiResponse(BaseModel):
    """Describe where the policy a reconciliation used was attached."""

    model_config = ConfigDict(from_attributes=True)

    type: str
    path: list[str]


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
    policy_id: str
    policy_name: str
    policy_deleted: bool
    policy_version: int
    policy_target: ReconciliationPolicyTargetApiResponse | None
