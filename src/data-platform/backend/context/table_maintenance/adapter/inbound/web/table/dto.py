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
    matched_rule_id: str | None = Field(
        description=(
            "The `dr-` id of the rule that decided the table, in the version `matched_policy_version` of the "
            "discovery policy `matched_policy_id`; null when the policy's no-match outcome decided it."
        )
    )
    matched_policy_id: str = Field(
        description=(
            "The `dp-` id of the discovery policy that decided whether the table is managed: the policy of its "
            "nearest attachment, or the default when nothing on its walk is attached."
        )
    )
    matched_policy_version: int = Field(description="The version of that discovery policy that decided the table.")
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


class TableMetricValuesApiResponse(BaseModel):
    """Carry the measured counts of a table's files, manifests and snapshots."""

    model_config = ConfigDict(from_attributes=True)

    data_files: int
    position_delete_files: int
    equality_delete_files: int
    deletion_vectors: int
    data_size_bytes: int
    data_records: int
    position_delete_records: int
    equality_delete_records: int
    reducible_files: int
    manifests: int
    manifests_size_bytes: int
    manifest_added_entries: int
    manifest_existing_entries: int
    manifest_deleted_entries: int
    snapshots: int


class TableCurrentMetricsApiResponse(BaseModel):
    """Carry a table's newest metrics; both fields are null for a table that is not managed or not reconciled yet."""

    model_config = ConfigDict(from_attributes=True)

    observed_at: datetime | None
    metrics: TableMetricValuesApiResponse | None


class TableMetricTrendPointApiResponse(BaseModel):
    """Carry one moment of a table's metric trend."""

    model_config = ConfigDict(from_attributes=True)

    at: datetime
    values: dict[str, float | None] = Field(
        description=(
            "Every metric count and the two manifest averages (`manifest_average_size_bytes`, "
            "`manifest_average_entries`) at this moment; null where there is no value."
        )
    )


class TableMetricTrendsApiResponse(BaseModel):
    """Carry a table's metric trend: one point per step from `start` to `end` inclusive."""

    model_config = ConfigDict(from_attributes=True)

    time_range: str
    step_seconds: int
    start: datetime
    end: datetime
    points: list[TableMetricTrendPointApiResponse]


class TableCommitApiResponse(BaseModel):
    """Describe one commit of a table."""

    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    parent_id: str | None
    committed_at: datetime
    operation: str | None
    writer: str
    schema_id: int | None
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
