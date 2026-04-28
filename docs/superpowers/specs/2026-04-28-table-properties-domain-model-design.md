# Table Properties Domain Model Design

**Date:** 2026-04-28
**Status:** Approved

## Context

The table-maintenance service needs to display and modify Iceberg table metadata (write modes, distribution modes, format settings, etc.). Currently, `Table` aggregate stores properties as `dict[str, str]` — raw Iceberg key-value pairs with no domain semantics.

## Decision

Replace `properties: dict[str, str]` on the `Table` aggregate with a fully typed `TableProperties` value object composed of nested VOs that mirror the Iceberg property key hierarchy.

## Scope

All Iceberg table properties in a single phase:

- Write mode: `write.{merge,update,delete}.mode`, isolation level, distribution mode
- File format: `write.format.default`, `write.parquet.*`, `write.delete.parquet.*`
- File sizing: `write.target-file-size-bytes`, `write.delete.target-file-size-bytes`
- Manifest: `write.manifest.*`
- Metadata: `write.metadata.*`
- Commit/retry: `write.commit.*`
- Metrics: `write.metrics.*`
- Flags: `write.upsert.enabled`, `write.wap.enabled`, `write.object-storage.enabled`
- Read: `read.split.*`, `read.parquet.*`, `read.orc.*`
- Format version: `format-version`

## Domain Model

### Enums

```python
class WriteMode(StrEnum):
    COPY_ON_WRITE = "copy-on-write"
    MERGE_ON_READ = "merge-on-read"

class DistributionMode(StrEnum):
    NONE = "none"
    HASH = "hash"
    RANGE = "range"

class IsolationLevel(StrEnum):
    SERIALIZABLE = "serializable"
    SNAPSHOT = "snapshot"
```

### Leaf Value Objects

```python
# Reused by merge and update operations
class OperationProperties(ValueObject):
    mode: WriteMode | None = None
    isolation_level: IsolationLevel | None = None
    distribution_mode: DistributionMode | None = None

# Delete has additional format/parquet settings
class DeleteProperties(ValueObject):
    mode: WriteMode | None = None
    isolation_level: IsolationLevel | None = None
    distribution_mode: DistributionMode | None = None
    format_default: str | None = None
    target_file_size_bytes: int | None = None
    parquet: ParquetProperties | None = None

class ParquetProperties(ValueObject):
    compression_codec: str | None = None
    compression_level: int | None = None
    row_group_size_bytes: int | None = None
    page_size_bytes: int | None = None
    dict_size_bytes: int | None = None

class FormatProperties(ValueObject):
    default: str | None = None

class ManifestProperties(ValueObject):
    target_size_bytes: int | None = None
    min_merge_count: int | None = None
    merge_enabled: bool | None = None

class MetadataProperties(ValueObject):
    compression_codec: str | None = None
    delete_after_commit_enabled: bool | None = None
    previous_versions_max: int | None = None

class CommitProperties(ValueObject):
    num_retries: int | None = None
    retry_min_wait_ms: int | None = None
    retry_max_wait_ms: int | None = None
    total_retry_time_ms: int | None = None

class MetricsProperties(ValueObject):
    default_mode: str | None = None

class SplitProperties(ValueObject):
    size: int | None = None
    lookback: int | None = None
    open_file_cost: int | None = None

class ReadParquetProperties(ValueObject):
    vectorization_enabled: bool | None = None
    batch_size: int | None = None

class ReadOrcProperties(ValueObject):
    vectorization_enabled: bool | None = None
    batch_size: int | None = None
```

### Composite Value Objects

```python
class WriteProperties(ValueObject):
    merge: OperationProperties | None = None
    update: OperationProperties | None = None
    delete: DeleteProperties | None = None
    distribution_mode: DistributionMode | None = None
    format: FormatProperties | None = None
    parquet: ParquetProperties | None = None
    target_file_size_bytes: int | None = None
    manifest: ManifestProperties | None = None
    metadata: MetadataProperties | None = None
    commit: CommitProperties | None = None
    metrics: MetricsProperties | None = None
    upsert_enabled: bool | None = None
    wap_enabled: bool | None = None
    object_storage_enabled: bool | None = None

class ReadProperties(ValueObject):
    split: SplitProperties | None = None
    parquet: ReadParquetProperties | None = None
    orc: ReadOrcProperties | None = None

class TableProperties(ValueObject):
    format_version: int | None = None
    write: WriteProperties | None = None
    read: ReadProperties | None = None
```

### Table Aggregate Change

```python
# Before
class Table(AggregateRoot[TableId]):
    ...
    properties: dict[str, str]

# After
class Table(AggregateRoot[TableId]):
    ...
    properties: TableProperties
```

## Directory Structure

```
application/domain/model/catalog/
├── table.py
├── table_properties/
│   ├── __init__.py
│   ├── table_properties.py
│   ├── write_properties.py
│   ├── read_properties.py
│   ├── operation_properties.py
│   ├── delete_properties.py
│   ├── format_properties.py
│   ├── parquet_properties.py
│   ├── manifest_properties.py
│   ├── metadata_properties.py
│   ├── commit_properties.py
│   ├── metrics_properties.py
│   ├── split_properties.py
│   ├── read_parquet_properties.py
│   ├── read_orc_properties.py
│   ├── write_mode.py
│   ├── isolation_level.py
│   └── distribution_mode.py
```

## Use Cases

### Read (existing, modified)

`GetTableService` continues to return `properties: dict[str, str]` in its output DTO. The service converts `TableProperties` back to dict using `table_properties_to_dict()`. The typed structure's value stays in the domain and service layers.

### Write (new)

New `UpdateTableProperties` use case:

```
application/port/inbound/catalog/update_table_properties/
├── input.py       # UpdateTablePropertiesInput {namespace, table, properties: dict[str, str | None]}
├── output.py      # UpdateTablePropertiesOutput
└── use_case.py    # UpdateTablePropertiesUseCase

application/port/outbound/catalog/update_table_properties/
├── gateway.py     # UpdateTablePropertiesGateway
└── input.py       # UpdateTablePropertiesInput {namespace, table, updates: dict[str, str], removals: list[str]}

application/service/catalog/update_table_properties.py
```

**Flow:**
1. API adapter receives `{"write.merge.mode": "merge-on-read", "write.delete.mode": null}`
2. Inbound `UpdateTablePropertiesInput` with `properties: dict[str, str | None]` (None = remove)
3. Service validates keys, splits into updates and removals
4. `UpdateTablePropertiesGateway.execute()` sends to Iceberg catalog
5. Returns updated properties (re-read via `ReadCatalogGateway.load_table()`)

## Adapter Layer

### Conversion Functions

```
adapter/outbound/catalog/
├── dict_to_table_properties.py              # dict[str,str] -> TableProperties
├── table_properties_to_dict.py              # TableProperties -> dict[str,str]
├── read_catalog_iceberg_gateway.py          # (modified to use dict_to_table_properties)
└── update_table_properties_iceberg_gateway.py  # new
```

### dict_to_table_properties

Maps Iceberg property keys to nested VO structure. Helper functions:
- `_int(v)` — parse optional int
- `_bool(v)` — parse optional bool
- `_enum(cls, v)` — parse optional StrEnum value

### table_properties_to_dict

Flattens nested VO structure back to `dict[str, str]` for output DTOs and gateway input.

## CLAUDE.md Update

Add `Update` to the gateway verb vocabulary:

> **Gateway verb vocabulary** (new verbs require review): `Read`, `Submit`, `Send`, `Publish`, `Poll`, `Sync`, `Write`, `Delete`, `Update`.

## Design Rationale

- **All fields `| None`**: Iceberg properties are optional with server-side defaults. `None` means "not set / use Iceberg default."
- **Nested VOs mirror Iceberg key hierarchy**: `write.merge.mode` maps to `properties.write.merge.mode`. Predictable structure, simple conversion logic.
- **`OperationProperties` reuse**: merge and update share the same shape (mode, isolation_level, distribution_mode).
- **`DeleteProperties` is standalone**: delete has additional format and parquet settings not shared with merge/update. Composition over inheritance.
- **Output stays `dict[str, str]`**: Avoids explosion of output DTOs. Typed structure's value is in domain validation and service logic.
- **`table_properties/` subdirectory**: Keeps `catalog/` clean. ~17 files is a coherent sub-package, consistent with existing `job_run/` and `job/` patterns.
