"""Define the maintenance run API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TableMaintenanceRunAttemptApiResponse(BaseModel):
    """Describe one attempt of a maintenance run: its job, size, how it ended and what followed it."""

    model_config = ConfigDict(from_attributes=True)

    attempt: int
    size: str
    status: str
    job_name: str | None
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


class TableMaintenanceRunPartitionFieldApiResponse(BaseModel):
    """Describe one field of a partition spec: the column it is computed from and its transform."""

    column: str = Field(description="The source column, dot-joined for a nested column.")
    transform: str = Field(description="Iceberg's transform, such as `identity`, `day` or `bucket[16]`.")


class TableMaintenanceRunPartitionSpecApiResponse(BaseModel):
    """Describe the partitions of one partition spec a compaction rewrites."""

    spec_id: int
    fields: list[TableMaintenanceRunPartitionFieldApiResponse]
    partitions: list[list[str | None]] = Field(
        description=(
            "One entry per partition, one value per field, as Iceberg prints it "
            "(`2026-11-20` for a day); null is a null partition."
        )
    )


class TableMaintenanceRunApiResponse(BaseModel):
    """Describe a maintenance run: one operation on one table, and the attempts that make up its timeline."""

    model_config = ConfigDict(from_attributes=True)

    run_id: str
    table_uuid: str
    execution_ref: str
    trigger: str
    priority: str = Field(description="The priority this run was started with, `P0` to `P3`.")
    operation: str = Field(description="The one operation this run does.")
    status: str
    settings: dict[str, Any] = Field(
        description=(
            "What each job of this run is set to do: the target file size, ages and counts the platform "
            "resolved, and the policy's options; an option not listed is the procedure's default."
        )
    )
    partitions: list[TableMaintenanceRunPartitionSpecApiResponse] = Field(
        description="The partitions each job of a compaction rewrites, per partition spec; empty: the whole table."
    )
    metrics: dict[str, int] = Field(description="The numbers the procedure returned.")
    error: str | None
    skip_reason: str | None = Field(description="Why the run was skipped; set only when status is skipped.")
    created_at: datetime
    started_at: datetime | None = Field(description="When the first attempt was submitted; null while pending.")
    finished_at: datetime | None
    attempts: list[TableMaintenanceRunAttemptApiResponse] = Field(description="Every attempt, oldest first.")


class ForwardTableMaintenanceResultApiRequest(BaseModel):
    """Carry the result a Spark job reports for one operation attempt."""

    model_config = ConfigDict(extra="ignore")

    run_id: str | None = None
    operation: str | None = None
    attempt: int
    succeeded: bool
    metrics: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


class ForwardTableMaintenanceResultApiResponse(BaseModel):
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
