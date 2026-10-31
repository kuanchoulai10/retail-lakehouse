"""Define the table API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel


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


class TableMetadataApiResponse(BaseModel):
    """Describe the catalog definition and current totals of a table."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str
    format_version: int
    location: str
    properties: dict[str, str]
    schema_fields: list[dict[str, Any]]
    specs: list[dict[str, Any]]
    current_snapshot_id: int | None
    snapshot_count: int
    last_committed_at: datetime | None
    total_records: int | None
    total_data_files: int | None
    total_delete_files: int | None
    total_files_size_bytes: int | None


class TableCommitApiResponse(BaseModel):
    """Describe one commit of a table."""

    model_config = ConfigDict(from_attributes=True)

    snapshot_id: int
    parent_id: int | None
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
