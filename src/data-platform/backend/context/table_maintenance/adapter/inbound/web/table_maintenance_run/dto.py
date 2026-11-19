"""Define the maintenance run API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TableMaintenanceRunAttemptApiResponse(BaseModel):
    """Describe one attempt of a maintenance operation: its size, how it ended and what followed it."""

    model_config = ConfigDict(from_attributes=True)

    attempt: int
    size: str | None
    status: str
    started_at: datetime
    finished_at: datetime | None
    failure_class: str | None
    error: str | None
    event_log_finished: bool | None
    next_step: str | None
    next_size: str | None


class TableMaintenanceRunOperationApiResponse(BaseModel):
    """Describe one operation of a maintenance run, its latest attempt and every attempt it made."""

    model_config = ConfigDict(from_attributes=True)

    operation: str
    status: str
    attempts: int
    started_at: datetime | None
    finished_at: datetime | None
    job_name: str | None
    metrics: dict[str, int]
    error: str | None
    expected_files: int | None
    attempt_history: list[TableMaintenanceRunAttemptApiResponse]


class TableMaintenanceRunApiResponse(BaseModel):
    """Describe a maintenance run."""

    model_config = ConfigDict(from_attributes=True)

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    priority: str
    status: str
    operations: list[TableMaintenanceRunOperationApiResponse]
    created_at: datetime
    finished_at: datetime | None


class ProcessTableMaintenanceCallbackApiRequest(BaseModel):
    """Carry the result a Spark job reports for one operation attempt."""

    model_config = ConfigDict(extra="ignore")

    run_id: str | None = None
    operation: str | None = None
    attempt: int
    succeeded: bool
    metrics: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


class ProcessTableMaintenanceCallbackApiResponse(BaseModel):
    """Tell whether the callback was accepted."""

    model_config = ConfigDict(from_attributes=True)

    accepted: bool
