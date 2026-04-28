"""Catalog API response DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SchemaFieldApiResponse(BaseModel):
    """A single field in a table schema."""

    id: int
    name: str
    type: str
    required: bool


class SchemaApiResponse(BaseModel):
    """Table schema with its fields."""

    fields: list[SchemaFieldApiResponse]


class NamespacesApiResponse(BaseModel):
    """Response for listing namespaces."""

    namespaces: list[str]


class TablesApiResponse(BaseModel):
    """Response for listing tables."""

    tables: list[str]


class TableDetailApiResponse(BaseModel):
    """Response for table metadata."""

    table: str
    namespace: str
    location: str
    current_snapshot_id: int | None
    schema_: SchemaApiResponse = Field(alias="schema")
    properties: dict[str, str]

    model_config = {"populate_by_name": True}


class SnapshotApiResponse(BaseModel):
    """A single snapshot."""

    snapshot_id: int
    parent_id: int | None
    timestamp_ms: int
    summary: dict[str, str]


class SnapshotsApiResponse(BaseModel):
    """Response for listing snapshots."""

    snapshots: list[SnapshotApiResponse]


class BranchApiResponse(BaseModel):
    """A single branch ref."""

    name: str
    snapshot_id: int
    max_snapshot_age_ms: int | None
    max_ref_age_ms: int | None
    min_snapshots_to_keep: int | None


class BranchesApiResponse(BaseModel):
    """Response for listing branches."""

    branches: list[BranchApiResponse]


class TagApiResponse(BaseModel):
    """A single tag ref."""

    name: str
    snapshot_id: int
    max_ref_age_ms: int | None


class TagsApiResponse(BaseModel):
    """Response for listing tags."""

    tags: list[TagApiResponse]
