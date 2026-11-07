"""Define the table API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel, field_validator


class TableApiResponse(BaseModel):
    """Describe a table."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str
    catalog: str
    namespace: str
    table: str
    status: str
    selection: str
    settings: dict[str, Any] | None
    matched_rule_id: str | None
    source_preset_id: str | None
    operation_states: dict[str, dict[str, Any]]
    registered_at: datetime
    updated_at: datetime


class TableHealthOperationApiResponse(BaseModel):
    """Describe the scheduler's verdict on one maintenance operation."""

    model_config = ConfigDict(from_attributes=True)

    operation: str
    verdict: str
    measured: int | None
    threshold: int | None
    next_eligible_at: datetime | None
    qualifying_partitions: int | None
    size_bytes: int | None
    size_source: str | None


class TableHealthApiResponse(BaseModel):
    """Describe the maintenance health of a table."""

    model_config = ConfigDict(from_attributes=True)

    scheduled: bool
    not_scheduled_reason: str | None
    operations: list[TableHealthOperationApiResponse]
    position_delete_files: int
    equality_delete_files: int


class TableStorageApiResponse(BaseModel):
    """Describe the storage of a table and what maintenance reclaimed."""

    model_config = ConfigDict(from_attributes=True)

    current_bytes: int
    current_files: int
    old_snapshot_bytes: int
    old_snapshot_files: int
    window_days: int
    reclaimed: dict[str, int]
    attempts_without_metrics: int


class TableCommitApiResponse(BaseModel):
    """Describe one commit of a table."""

    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    parent_id: str | None
    committed_at: datetime
    operation: str | None
    writer: str
    added_records: int | None
    deleted_records: int | None
    added_data_files: int | None
    deleted_data_files: int | None
    added_delete_files: int | None
    removed_delete_files: int | None
    summary: dict[str, str]

    @field_validator("snapshot_id", "parent_id", mode="before")
    @classmethod
    def _snapshot_ids_as_strings(cls, value: object) -> object:
        """Carry the 64-bit snapshot ids as strings so JavaScript keeps every digit."""
        return str(value) if isinstance(value, int) else value


class TableCommitsApiResponse(BaseModel):
    """Carry the commits of a table, newest first."""

    model_config = ConfigDict(from_attributes=True)

    items: list[TableCommitApiResponse]
    truncated: bool


class UpdateTableSettingsApiRequest(RootModel[dict[str, Any]]):
    """Carry the settings object that replaces the table settings."""


class IncludeTableApiRequest(BaseModel):
    """Carry the body that includes a table by hand."""

    model_config = ConfigDict(extra="forbid")

    catalog: str
    namespace: str
    table: str
    preset_id: str


class ExcludeTableApiRequest(BaseModel):
    """Carry the body that excludes a table by hand."""

    model_config = ConfigDict(extra="forbid")

    catalog: str
    namespace: str
    table: str


class TriggerTableMaintenanceApiRequest(BaseModel):
    """Carry the operations to run now."""

    model_config = ConfigDict(extra="forbid")

    operations: list[str]


class TriggerTableMaintenanceApiResponse(BaseModel):
    """Tell whether the trigger was accepted."""

    model_config = ConfigDict(from_attributes=True)

    accepted: bool
