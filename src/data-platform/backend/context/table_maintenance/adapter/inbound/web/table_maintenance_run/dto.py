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
    started_running_at: datetime | None = Field(
        description="When the attempt's Spark driver started running; null while the attempt waits in its queue."
    )
    finished_at: datetime | None
    failure_class: str | None
    error: str | None
    event_log_finished: bool | None
    next_step: str | None
    next_size: str | None


class TableMaintenanceRunFilterApiResponse(BaseModel):
    """Describe one where clause a compaction passes to rewrite_data_files, for one partition spec."""

    model_config = ConfigDict(from_attributes=True)

    spec_id: int
    where: str


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
    filters: list[TableMaintenanceRunFilterApiResponse] = Field(
        description=(
            "The where clauses each job of this operation passes to rewrite_data_files, "
            "one per partition spec; empty: the whole table."
        )
    )


class TableMaintenanceRunApiResponse(BaseModel):
    """Describe a maintenance run."""

    model_config = ConfigDict(from_attributes=True)

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    priority: str = Field(description="The priority this run was started with, `P0` to `P3`.")
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


class PlatformSettingApiResponse(BaseModel):
    """Describe one platform setting: a stable key, a label, its value and unit, and a one-sentence description.

    ``unit`` is null for a value that carries its own, such as ``768m``.
    """

    key: str
    label: str
    value: int | float | str
    unit: str | None
    description: str


class PlatformSettingsGroupApiResponse(BaseModel):
    """Describe one theme of platform settings: a stable key, a title and its settings in reading order."""

    key: str
    title: str
    items: list[PlatformSettingApiResponse]


class PlatformSettingsApiResponse(BaseModel):
    """Describe the platform-level settings the running component was started with, grouped by theme."""

    groups: list[PlatformSettingsGroupApiResponse]
