"""Define the table API DTOs.

Column types are text. A primitive is its Iceberg name: ``long``, ``string``, ``timestamptz``,
``decimal(10,2)``, ``fixed[16]``. A nested type uses this syntax, both in responses and in the
create request:

- ``struct<name: type, ...>``, for example ``struct<city: required string, zip: string>``;
- ``list<type>``, for example ``list<string>``;
- ``map<key, value>``, for example ``map<string, list<required int>>``.

A nested struct field, list element or map value prefixed with ``required`` is required;
without the prefix it is optional. Map keys are always required, so a key takes no prefix.
Nested field ids and docs are not part of the text. ``required`` is this API's syntax, not
Spark or Trino DDL: a client that builds DDL must translate it (``list`` to ``array``,
``struct`` to ``row`` in Trino, and drop or map ``required`` to ``NOT NULL`` where supported).

Snapshot ids are 64-bit, so the responses carry them as decimal strings, which a browser
cannot round (Ruling R9).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from context.catalog.adapter.inbound.web.shared import SchemaApiResponse


def _id_text(value: object) -> object:
    """Turn an int snapshot id into its exact decimal text; None and text pass through."""
    return str(value) if isinstance(value, int) else value


SnapshotIdText = Annotated[str, BeforeValidator(_id_text)]


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


class ResetTablePropertiesApiRequest(BaseModel):
    """Carry the loaded table's uuid and the property keys to reset to default; a custom key is deleted."""

    model_config = ConfigDict(extra="forbid")

    expected_uuid: str
    keys: list[str]


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
    """One snapshot; ids are decimal strings and ``summary`` holds the summary's keys other than ``operation``."""

    model_config = ConfigDict(from_attributes=True)

    id: SnapshotIdText
    parent_id: SnapshotIdText | None
    timestamp_ms: int
    schema_id: int | None
    operation: str | None
    summary: dict[str, str]


class TableSummaryApiResponse(BaseModel):
    """The current snapshot's totals, each null when not reported."""

    model_config = ConfigDict(from_attributes=True)

    total_records: int | None
    total_data_files: int | None
    total_files_size: int | None


class CatalogTableApiResponse(BaseModel):
    """Describe an Iceberg table: everything the table page's Overview, Schema, Snapshots and Properties show."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    catalog: str
    namespace: list[str]
    name: str
    uuid: str
    format_version: int
    location: str
    current_snapshot_id: SnapshotIdText | None
    last_updated_ms: int
    table_schema: SchemaApiResponse = Field(serialization_alias="schema")
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


class CatalogTablePropertyApiResponse(BaseModel):
    """One table property next to its default.

    ``current_value`` is null when the table does not set the key. ``default_source`` is
    ``iceberg`` (Iceberg's own default, null when Iceberg has none), ``catalog`` (the catalog's
    ``table-default.<key>``), ``catalog_override`` (its ``table-override.<key>``: forced by the
    catalog, never resettable) or null for a custom key the catalog does not default.
    ``modified`` is a key set to something other than its default, or a custom key that is set;
    ``custom`` is a key the platform's catalogue of Iceberg properties does not know.
    """

    model_config = ConfigDict(from_attributes=True)

    key: str
    current_value: str | None
    default_value: str | None
    default_source: Literal["iceberg", "catalog", "catalog_override"] | None
    modified: bool
    custom: bool
    resettable: bool
    description: str | None


class CatalogTablePropertiesApiResponse(BaseModel):
    """Every property of a table next to its default, ordered by key, and the Iceberg version of the defaults."""

    uuid: str
    iceberg_version: str
    properties: list[CatalogTablePropertyApiResponse]


class SchemaChangeCountsApiResponse(BaseModel):
    """How many fields a schema version added, removed, renamed, retyped, made required or optional, or redocumented."""

    model_config = ConfigDict(from_attributes=True)

    added: int
    removed: int
    renamed: int
    type_changed: int
    nullability_changed: int
    doc_changed: int


class CatalogTableSchemaVersionApiResponse(BaseModel):
    """One schema version: its id, the version below it, whether it is current, its column count and what it changed.

    ``changes`` is null for the first version, which has nothing to compare with.
    """

    model_config = ConfigDict(from_attributes=True)

    schema_id: int
    previous_schema_id: int | None
    current: bool
    column_count: int
    changes: SchemaChangeCountsApiResponse | None


class CatalogTableSchemaVersionsApiResponse(BaseModel):
    """Every schema version of a table, newest id first, and the id of the current one (not always the highest)."""

    current_schema_id: int
    versions: list[CatalogTableSchemaVersionApiResponse]


class SchemaFieldComparisonApiResponse(BaseModel):
    """One field of a schema comparison matched by field id, with its current and previous state.

    The current side is null for a removed field and the previous side null for an added one;
    a path lists the names from the top-level column down, and ``type`` is the outer type
    (``struct``, ``list``, ``map`` or the primitive). ``changes`` is empty for an unchanged field.
    """

    model_config = ConfigDict(from_attributes=True)

    field_id: int
    depth: int
    path: list[str] | None
    previous_path: list[str] | None
    type: str | None
    previous_type: str | None
    required: bool | None
    previous_required: bool | None
    doc: str | None
    previous_doc: str | None
    changes: list[Literal["added", "removed", "renamed", "type_changed", "nullability_changed", "doc_changed"]]


class CatalogTableSchemaComparisonApiResponse(BaseModel):
    """A schema version set against a base version, one row per field; the base is null for the first version."""

    base_schema_id: int | None
    schema_id: int
    fields: list[SchemaFieldComparisonApiResponse]


class PartitionChangeCountsApiResponse(BaseModel):
    """How many partition fields of a spec version were added, removed, renamed or given another transform."""

    model_config = ConfigDict(from_attributes=True)

    added: int
    removed: int
    renamed: int
    transform_changed: int


class CatalogTablePartitionSpecVersionApiResponse(BaseModel):
    """One partition spec version: its id, the version below it, whether it is the default, its field count and changes.

    ``changes`` is null for the first version, which has nothing to compare with.
    """

    model_config = ConfigDict(from_attributes=True)

    spec_id: int
    previous_spec_id: int | None
    default: bool
    field_count: int
    changes: PartitionChangeCountsApiResponse | None


class CatalogTablePartitionSpecVersionsApiResponse(BaseModel):
    """Every partition spec version of a table, newest id first, and the id of the default one."""

    default_spec_id: int
    versions: list[CatalogTablePartitionSpecVersionApiResponse]


class PartitionFieldComparisonApiResponse(BaseModel):
    """One partition field of a spec comparison, with its current and previous state and ``transform(column)`` text.

    The current side is null for a removed field and the previous side null for an added one;
    a field whose transform changed carries its new field id and the old one in ``previous_field_id``.
    ``changes`` is empty for an unchanged field.
    """

    model_config = ConfigDict(from_attributes=True)

    field_id: int | None
    previous_field_id: int | None
    name: str | None
    previous_name: str | None
    source_path: list[str] | None
    previous_source_path: list[str] | None
    transform: str | None
    previous_transform: str | None
    changes: list[Literal["added", "removed", "renamed", "transform_changed"]]
    expression: str | None
    previous_expression: str | None


class CatalogTablePartitionSpecComparisonApiResponse(BaseModel):
    """A partition spec version set against a base version, one row per field; the base is null for the first one."""

    base_spec_id: int | None
    spec_id: int
    fields: list[PartitionFieldComparisonApiResponse]
