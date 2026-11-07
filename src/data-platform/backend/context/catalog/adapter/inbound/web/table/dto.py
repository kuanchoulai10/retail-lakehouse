"""Define the table API DTOs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SchemaFieldApiRequest(BaseModel):
    """One column of the create table form; ``type`` is an Iceberg primitive or the nested type syntax."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    required: bool = True
    doc: str | None = None


class PartitionFieldApiRequest(BaseModel):
    """One partition field of the create table form: the top-level column and its transform."""

    model_config = ConfigDict(extra="forbid")

    source_column: str
    transform: str


class CreateTableApiRequest(BaseModel):
    """Carry the create table form: name, schema fields, optional partition fields, optional location, properties."""

    model_config = ConfigDict(extra="forbid")

    name: str
    schema_fields: list[SchemaFieldApiRequest]
    partition_fields: list[PartitionFieldApiRequest] = Field(default_factory=list)
    location: str | None = None
    properties: dict[str, str] = Field(default_factory=dict)


class RenameTableApiRequest(BaseModel):
    """Name where the table goes: a namespace of the same catalog, by parts, and a name."""

    model_config = ConfigDict(extra="forbid")

    target_namespace: list[str]
    target_name: str


class UpdateTablePropertiesApiRequest(BaseModel):
    """Carry the loaded table's uuid, the properties to set and the property keys to remove."""

    model_config = ConfigDict(extra="forbid")

    expected_uuid: str
    updates: dict[str, str] = Field(default_factory=dict)
    removals: list[str] = Field(default_factory=list)


class SchemaFieldApiResponse(BaseModel):
    """One top-level column; ``type`` is text."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    required: bool
    doc: str | None


class TableSchemaApiResponse(BaseModel):
    """The current schema."""

    model_config = ConfigDict(from_attributes=True)

    schema_id: int
    fields: list[SchemaFieldApiResponse]


class PartitionFieldApiResponse(BaseModel):
    """One partition field."""

    model_config = ConfigDict(from_attributes=True)

    source_id: int
    field_id: int
    name: str
    transform: str


class PartitionSpecApiResponse(BaseModel):
    """The default partition spec; no fields means unpartitioned."""

    model_config = ConfigDict(from_attributes=True)

    spec_id: int
    fields: list[PartitionFieldApiResponse]


class SortFieldApiResponse(BaseModel):
    """One sort field; ``direction`` is ``asc`` or ``desc``, ``null_order`` ``nulls-first`` or ``nulls-last``."""

    model_config = ConfigDict(from_attributes=True)

    source_id: int
    transform: str
    direction: str
    null_order: str


class SortOrderApiResponse(BaseModel):
    """The default sort order; no fields means unsorted."""

    model_config = ConfigDict(from_attributes=True)

    order_id: int
    fields: list[SortFieldApiResponse]


class SnapshotApiResponse(BaseModel):
    """One snapshot; ``summary`` holds the snapshot summary's keys other than ``operation``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None
    timestamp_ms: int
    operation: str | None
    summary: dict[str, str]


class TableSummaryApiResponse(BaseModel):
    """The current snapshot's totals, each null when not reported."""

    model_config = ConfigDict(from_attributes=True)

    total_records: int | None
    total_data_files: int | None
    total_files_size: int | None


class TableApiResponse(BaseModel):
    """Describe an Iceberg table: everything the table page's Overview, Schema, Snapshots and Properties show."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    catalog: str
    namespace: list[str]
    name: str
    uuid: str
    format_version: int
    location: str
    current_snapshot_id: int | None
    last_updated_ms: int
    table_schema: TableSchemaApiResponse = Field(alias="schema")
    partition_spec: PartitionSpecApiResponse
    sort_order: SortOrderApiResponse
    snapshots: list[SnapshotApiResponse]
    properties: dict[str, str]
    summary: TableSummaryApiResponse


class TableIdentifierApiResponse(BaseModel):
    """Name a table in a listing or after a rename."""

    model_config = ConfigDict(from_attributes=True)

    catalog: str
    namespace: list[str]
    name: str
