"""Catalog API response DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SchemaFieldResponse(BaseModel):
    """A single field in a table schema."""

    id: int
    name: str
    type: str
    required: bool


class SchemaResponse(BaseModel):
    """Table schema with its fields."""

    fields: list[SchemaFieldResponse]


class NamespacesResponse(BaseModel):
    """Response for listing namespaces."""

    namespaces: list[str]


class TablesResponse(BaseModel):
    """Response for listing tables."""

    tables: list[str]


class TableDetailResponse(BaseModel):
    """Response for table metadata."""

    table: str
    namespace: str
    location: str
    current_snapshot_id: int | None
    schema_: SchemaResponse = Field(alias="schema")
    properties: dict[str, str]

    model_config = {"populate_by_name": True}


class SnapshotResponse(BaseModel):
    """A single snapshot."""

    snapshot_id: int
    parent_id: int | None
    timestamp_ms: int
    summary: dict[str, str]


class SnapshotsResponse(BaseModel):
    """Response for listing snapshots."""

    snapshots: list[SnapshotResponse]


class BranchResponse(BaseModel):
    """A single branch ref."""

    name: str
    snapshot_id: int
    max_snapshot_age_ms: int | None
    max_ref_age_ms: int | None
    min_snapshots_to_keep: int | None


class BranchesResponse(BaseModel):
    """Response for listing branches."""

    branches: list[BranchResponse]


class TagResponse(BaseModel):
    """A single tag ref."""

    name: str
    snapshot_id: int
    max_ref_age_ms: int | None


class TagsResponse(BaseModel):
    """Response for listing tags."""

    tags: list[TagResponse]
