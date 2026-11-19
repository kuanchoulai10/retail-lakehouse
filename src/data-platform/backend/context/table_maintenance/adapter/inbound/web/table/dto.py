"""Define the table API DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TableApiResponse(BaseModel):
    """Describe a table."""

    model_config = ConfigDict(from_attributes=True)

    uuid: str
    catalog: str
    namespace: str
    table: str
    status: str
    priority: str = Field(description="The table's maintenance priority, `P0` (urgent) to `P3` (the default).")
    matched_rule_id: str | None
    operation_states: dict[str, dict[str, Any]]
    registered_at: datetime
    updated_at: datetime
    last_committed_at: datetime | None = Field(
        description="When the table's newest commit landed in the catalog; null until one is seen."
    )
    last_discovered_at: datetime | None = Field(
        description=(
            "When discovery last saw the table: for a live table its catalog's last full scan, or its "
            "registration if that came later; for a dropped table the last time before it was dropped. "
            "Null when unknown."
        )
    )


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


class TriggerTableMaintenanceApiRequest(BaseModel):
    """Carry the operations to run now and, optionally, the priority of the run."""

    model_config = ConfigDict(extra="forbid")

    operations: list[str]
    priority: Literal["P0", "P1", "P2", "P3"] | None = None


class SetTablePriorityApiRequest(BaseModel):
    """Carry the priority to set on a table."""

    model_config = ConfigDict(extra="forbid")

    priority: Literal["P0", "P1", "P2", "P3"]


class TriggerTableMaintenanceApiResponse(BaseModel):
    """Tell whether the trigger was accepted."""

    model_config = ConfigDict(from_attributes=True)

    accepted: bool


class TriggerTableReconciliationApiResponse(BaseModel):
    """Tell whether the reconcile request was accepted."""

    model_config = ConfigDict(from_attributes=True)

    accepted: bool
