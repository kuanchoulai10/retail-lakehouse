"""Define the maintenance run API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceRunApiResponse(BaseModel):
    """Describe a maintenance run."""

    model_config = ConfigDict(from_attributes=True)

    run_id: str
    table_uuid: str
    trigger: str
    status: str
    operations: list[dict[str, Any]]
    created_at: datetime
    finished_at: datetime | None


class ProcessMaintenanceCallbackApiRequest(BaseModel):
    """Carry the result a Spark job reports for one operation attempt."""

    model_config = ConfigDict(extra="ignore")

    run_id: str | None = None
    operation: str | None = None
    attempt: int
    succeeded: bool
    metrics: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


class ProcessMaintenanceCallbackApiResponse(BaseModel):
    """Tell whether the callback was accepted."""

    model_config = ConfigDict(from_attributes=True)

    accepted: bool
