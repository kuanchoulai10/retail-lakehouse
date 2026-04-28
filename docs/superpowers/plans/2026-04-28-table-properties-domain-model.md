# Table Properties Domain Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `properties: dict[str, str]` on the Table aggregate with a fully typed `TableProperties` value object hierarchy, and add an `UpdateTableProperties` use case.

**Architecture:** Nested frozen dataclass VOs under `application/domain/model/catalog/table_properties/` mirror Iceberg's property key hierarchy. Adapter-layer converters handle `dict[str, str]` ↔ `TableProperties` translation. A new `UpdateTableProperties` use case provides write capability through a `UpdateTablePropertiesGateway` outbound port.

**Tech Stack:** Python 3.14, dataclasses (frozen), StrEnum, pytest, import-linter

**Spec:** `docs/superpowers/specs/2026-04-28-table-properties-domain-model-design.md`

**Working directory for all commands:** `src/table-maintenance/backend`

**Test command pattern:** `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest {path} -v`

**Lint command:** `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

---

## File Map

### New files — Domain Model (17 files)

| File | Responsibility |
|------|---------------|
| `application/domain/model/catalog/table_properties/__init__.py` | Re-export all public symbols |
| `application/domain/model/catalog/table_properties/write_mode.py` | `WriteMode` StrEnum |
| `application/domain/model/catalog/table_properties/distribution_mode.py` | `DistributionMode` StrEnum |
| `application/domain/model/catalog/table_properties/isolation_level.py` | `IsolationLevel` StrEnum |
| `application/domain/model/catalog/table_properties/parquet_properties.py` | `ParquetProperties` VO |
| `application/domain/model/catalog/table_properties/operation_properties.py` | `OperationProperties` VO (merge/update) |
| `application/domain/model/catalog/table_properties/delete_properties.py` | `DeleteProperties` VO |
| `application/domain/model/catalog/table_properties/format_properties.py` | `FormatProperties` VO |
| `application/domain/model/catalog/table_properties/manifest_properties.py` | `ManifestProperties` VO |
| `application/domain/model/catalog/table_properties/metadata_properties.py` | `MetadataProperties` VO |
| `application/domain/model/catalog/table_properties/commit_properties.py` | `CommitProperties` VO |
| `application/domain/model/catalog/table_properties/metrics_properties.py` | `MetricsProperties` VO |
| `application/domain/model/catalog/table_properties/split_properties.py` | `SplitProperties` VO |
| `application/domain/model/catalog/table_properties/read_parquet_properties.py` | `ReadParquetProperties` VO |
| `application/domain/model/catalog/table_properties/read_orc_properties.py` | `ReadOrcProperties` VO |
| `application/domain/model/catalog/table_properties/write_properties.py` | `WriteProperties` composite VO |
| `application/domain/model/catalog/table_properties/read_properties.py` | `ReadProperties` composite VO |
| `application/domain/model/catalog/table_properties/table_properties.py` | `TableProperties` top-level VO |

### New files — Adapter converters (2 files)

| File | Responsibility |
|------|---------------|
| `adapter/outbound/catalog/dict_to_table_properties.py` | `dict[str,str]` → `TableProperties` |
| `adapter/outbound/catalog/table_properties_to_dict.py` | `TableProperties` → `dict[str,str]` |

### New files — UpdateTableProperties use case (6 files)

| File | Responsibility |
|------|---------------|
| `application/port/inbound/catalog/update_table_properties/__init__.py` | Re-export |
| `application/port/inbound/catalog/update_table_properties/input.py` | `UpdateTablePropertiesInput` |
| `application/port/inbound/catalog/update_table_properties/output.py` | `UpdateTablePropertiesOutput` |
| `application/port/inbound/catalog/update_table_properties/use_case.py` | `UpdateTablePropertiesUseCase` |
| `application/port/outbound/catalog/update_table_properties/__init__.py` | Re-export |
| `application/port/outbound/catalog/update_table_properties/gateway.py` | `UpdateTablePropertiesGateway` |
| `application/port/outbound/catalog/update_table_properties/input.py` | `UpdateTablePropertiesInput` (primitive-only) |
| `application/service/catalog/update_table_properties.py` | `UpdateTablePropertiesService` |

### Modified files

| File | Change |
|------|--------|
| `application/domain/model/catalog/table.py` | `properties: dict[str, str]` → `properties: TableProperties` |
| `application/domain/model/catalog/__init__.py` | Add re-exports for `TableProperties` and enums |
| `application/port/inbound/catalog/__init__.py` | Add `UpdateTableProperties*` re-exports |
| `application/port/outbound/catalog/__init__.py` | Add `UpdateTablePropertiesGateway`, `UpdateTablePropertiesInput` |
| `application/port/outbound/__init__.py` | Add `UpdateTablePropertiesGateway`, `UpdateTablePropertiesInput` |
| `adapter/outbound/catalog/read_catalog_iceberg_gateway.py` | Use `dict_to_table_properties()` |
| `application/service/catalog/get_table.py` | Use `table_properties_to_dict()` for output |
| `CLAUDE.md` | Add `Update` to gateway verb vocabulary |

### Test files

| File | Tests |
|------|-------|
| `tests/application/domain/model/catalog/table_properties/test_write_mode.py` | Enum values |
| `tests/application/domain/model/catalog/table_properties/test_distribution_mode.py` | Enum values |
| `tests/application/domain/model/catalog/table_properties/test_isolation_level.py` | Enum values |
| `tests/application/domain/model/catalog/table_properties/test_parquet_properties.py` | VO creation, defaults |
| `tests/application/domain/model/catalog/table_properties/test_operation_properties.py` | VO creation, defaults |
| `tests/application/domain/model/catalog/table_properties/test_delete_properties.py` | VO creation, nested parquet |
| `tests/application/domain/model/catalog/table_properties/test_table_properties.py` | Full nested structure |
| `tests/adapter/outbound/catalog/test_dict_to_table_properties.py` | dict→VO conversion |
| `tests/adapter/outbound/catalog/test_table_properties_to_dict.py` | VO→dict conversion |
| `tests/application/service/catalog/test_update_table_properties.py` | Service logic |

---

## Task 1: Enums — WriteMode, DistributionMode, IsolationLevel

**Files:**
- Create: `application/domain/model/catalog/table_properties/write_mode.py`
- Create: `application/domain/model/catalog/table_properties/distribution_mode.py`
- Create: `application/domain/model/catalog/table_properties/isolation_level.py`
- Test: `tests/application/domain/model/catalog/table_properties/test_write_mode.py`
- Test: `tests/application/domain/model/catalog/table_properties/test_distribution_mode.py`
- Test: `tests/application/domain/model/catalog/table_properties/test_isolation_level.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/application/domain/model/catalog/table_properties/__init__.py` (empty).

Create `tests/application/domain/model/catalog/table_properties/test_write_mode.py`:

```python
"""Test the WriteMode enum."""

from __future__ import annotations

from enum import StrEnum

from application.domain.model.catalog.table_properties.write_mode import WriteMode


def test_write_mode_is_str_enum():
    assert issubclass(WriteMode, StrEnum)


def test_copy_on_write_value():
    assert WriteMode.COPY_ON_WRITE == "copy-on-write"


def test_merge_on_read_value():
    assert WriteMode.MERGE_ON_READ == "merge-on-read"


def test_from_string():
    assert WriteMode("copy-on-write") is WriteMode.COPY_ON_WRITE
```

Create `tests/application/domain/model/catalog/table_properties/test_distribution_mode.py`:

```python
"""Test the DistributionMode enum."""

from __future__ import annotations

from enum import StrEnum

from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode


def test_distribution_mode_is_str_enum():
    assert issubclass(DistributionMode, StrEnum)


def test_none_value():
    assert DistributionMode.NONE == "none"


def test_hash_value():
    assert DistributionMode.HASH == "hash"


def test_range_value():
    assert DistributionMode.RANGE == "range"
```

Create `tests/application/domain/model/catalog/table_properties/test_isolation_level.py`:

```python
"""Test the IsolationLevel enum."""

from __future__ import annotations

from enum import StrEnum

from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel


def test_isolation_level_is_str_enum():
    assert issubclass(IsolationLevel, StrEnum)


def test_serializable_value():
    assert IsolationLevel.SERIALIZABLE == "serializable"


def test_snapshot_value():
    assert IsolationLevel.SNAPSHOT == "snapshot"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/catalog/table_properties/ -v`

Expected: FAIL with `ModuleNotFoundError` — the enum modules don't exist yet.

- [ ] **Step 3: Create the enum files**

Create `application/domain/model/catalog/table_properties/write_mode.py`:

```python
"""Define the WriteMode enumeration."""

from enum import StrEnum


class WriteMode(StrEnum):
    """Iceberg write operation mode."""

    COPY_ON_WRITE = "copy-on-write"
    MERGE_ON_READ = "merge-on-read"
```

Create `application/domain/model/catalog/table_properties/distribution_mode.py`:

```python
"""Define the DistributionMode enumeration."""

from enum import StrEnum


class DistributionMode(StrEnum):
    """Iceberg write distribution mode."""

    NONE = "none"
    HASH = "hash"
    RANGE = "range"
```

Create `application/domain/model/catalog/table_properties/isolation_level.py`:

```python
"""Define the IsolationLevel enumeration."""

from enum import StrEnum


class IsolationLevel(StrEnum):
    """Iceberg write isolation level."""

    SERIALIZABLE = "serializable"
    SNAPSHOT = "snapshot"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/catalog/table_properties/ -v`

Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/application/domain/model/catalog/table_properties/ src/table-maintenance/backend/tests/application/domain/model/catalog/table_properties/
git commit -m "feat(catalog): add WriteMode, DistributionMode, IsolationLevel enums"
```

---

## Task 2: Leaf Value Objects — ParquetProperties, FormatProperties, ManifestProperties, MetadataProperties, CommitProperties, MetricsProperties, SplitProperties, ReadParquetProperties, ReadOrcProperties

**Files:**
- Create: `application/domain/model/catalog/table_properties/parquet_properties.py`
- Create: `application/domain/model/catalog/table_properties/format_properties.py`
- Create: `application/domain/model/catalog/table_properties/manifest_properties.py`
- Create: `application/domain/model/catalog/table_properties/metadata_properties.py`
- Create: `application/domain/model/catalog/table_properties/commit_properties.py`
- Create: `application/domain/model/catalog/table_properties/metrics_properties.py`
- Create: `application/domain/model/catalog/table_properties/split_properties.py`
- Create: `application/domain/model/catalog/table_properties/read_parquet_properties.py`
- Create: `application/domain/model/catalog/table_properties/read_orc_properties.py`
- Test: `tests/application/domain/model/catalog/table_properties/test_parquet_properties.py`

- [ ] **Step 1: Write the failing test for ParquetProperties**

Create `tests/application/domain/model/catalog/table_properties/test_parquet_properties.py`:

```python
"""Test the ParquetProperties value object."""

from __future__ import annotations

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.parquet_properties import ParquetProperties


def test_is_value_object():
    assert issubclass(ParquetProperties, ValueObject)


def test_all_defaults_none():
    p = ParquetProperties()
    assert p.compression_codec is None
    assert p.compression_level is None
    assert p.row_group_size_bytes is None
    assert p.page_size_bytes is None
    assert p.dict_size_bytes is None


def test_with_values():
    p = ParquetProperties(
        compression_codec="zstd",
        compression_level=3,
        row_group_size_bytes=134217728,
        page_size_bytes=1048576,
        dict_size_bytes=2097152,
    )
    assert p.compression_codec == "zstd"
    assert p.compression_level == 3
    assert p.row_group_size_bytes == 134217728


def test_frozen():
    p = ParquetProperties()
    try:
        p.compression_codec = "snappy"  # type: ignore[misc]
        assert False, "Should be frozen"
    except AttributeError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/catalog/table_properties/test_parquet_properties.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create all 9 leaf VO files**

Create `application/domain/model/catalog/table_properties/parquet_properties.py`:

```python
"""Define the ParquetProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ParquetProperties(ValueObject):
    """Parquet file format tuning properties."""

    compression_codec: str | None = None
    compression_level: int | None = None
    row_group_size_bytes: int | None = None
    page_size_bytes: int | None = None
    dict_size_bytes: int | None = None
```

Create `application/domain/model/catalog/table_properties/format_properties.py`:

```python
"""Define the FormatProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class FormatProperties(ValueObject):
    """Default file format properties."""

    default: str | None = None
```

Create `application/domain/model/catalog/table_properties/manifest_properties.py`:

```python
"""Define the ManifestProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ManifestProperties(ValueObject):
    """Manifest file management properties."""

    target_size_bytes: int | None = None
    min_merge_count: int | None = None
    merge_enabled: bool | None = None
```

Create `application/domain/model/catalog/table_properties/metadata_properties.py`:

```python
"""Define the MetadataProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class MetadataProperties(ValueObject):
    """Table metadata management properties."""

    compression_codec: str | None = None
    delete_after_commit_enabled: bool | None = None
    previous_versions_max: int | None = None
```

Create `application/domain/model/catalog/table_properties/commit_properties.py`:

```python
"""Define the CommitProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class CommitProperties(ValueObject):
    """Commit retry configuration properties."""

    num_retries: int | None = None
    retry_min_wait_ms: int | None = None
    retry_max_wait_ms: int | None = None
    total_retry_time_ms: int | None = None
```

Create `application/domain/model/catalog/table_properties/metrics_properties.py`:

```python
"""Define the MetricsProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class MetricsProperties(ValueObject):
    """Write metrics configuration properties."""

    default_mode: str | None = None
```

Create `application/domain/model/catalog/table_properties/split_properties.py`:

```python
"""Define the SplitProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class SplitProperties(ValueObject):
    """Read split planning properties."""

    size: int | None = None
    lookback: int | None = None
    open_file_cost: int | None = None
```

Create `application/domain/model/catalog/table_properties/read_parquet_properties.py`:

```python
"""Define the ReadParquetProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ReadParquetProperties(ValueObject):
    """Parquet read optimization properties."""

    vectorization_enabled: bool | None = None
    batch_size: int | None = None
```

Create `application/domain/model/catalog/table_properties/read_orc_properties.py`:

```python
"""Define the ReadOrcProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class ReadOrcProperties(ValueObject):
    """ORC read optimization properties."""

    vectorization_enabled: bool | None = None
    batch_size: int | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/catalog/table_properties/ -v`

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/application/domain/model/catalog/table_properties/ src/table-maintenance/backend/tests/application/domain/model/catalog/table_properties/
git commit -m "feat(catalog): add leaf value objects for table properties"
```

---

## Task 3: OperationProperties and DeleteProperties

**Files:**
- Create: `application/domain/model/catalog/table_properties/operation_properties.py`
- Create: `application/domain/model/catalog/table_properties/delete_properties.py`
- Test: `tests/application/domain/model/catalog/table_properties/test_operation_properties.py`
- Test: `tests/application/domain/model/catalog/table_properties/test_delete_properties.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/application/domain/model/catalog/table_properties/test_operation_properties.py`:

```python
"""Test the OperationProperties value object."""

from __future__ import annotations

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.operation_properties import OperationProperties
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode


def test_is_value_object():
    assert issubclass(OperationProperties, ValueObject)


def test_all_defaults_none():
    p = OperationProperties()
    assert p.mode is None
    assert p.isolation_level is None
    assert p.distribution_mode is None


def test_with_values():
    p = OperationProperties(
        mode=WriteMode.MERGE_ON_READ,
        isolation_level=IsolationLevel.SNAPSHOT,
        distribution_mode=DistributionMode.HASH,
    )
    assert p.mode == WriteMode.MERGE_ON_READ
    assert p.isolation_level == IsolationLevel.SNAPSHOT
    assert p.distribution_mode == DistributionMode.HASH
```

Create `tests/application/domain/model/catalog/table_properties/test_delete_properties.py`:

```python
"""Test the DeleteProperties value object."""

from __future__ import annotations

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.delete_properties import DeleteProperties
from application.domain.model.catalog.table_properties.parquet_properties import ParquetProperties
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode


def test_is_value_object():
    assert issubclass(DeleteProperties, ValueObject)


def test_all_defaults_none():
    p = DeleteProperties()
    assert p.mode is None
    assert p.isolation_level is None
    assert p.distribution_mode is None
    assert p.format_default is None
    assert p.target_file_size_bytes is None
    assert p.parquet is None


def test_with_nested_parquet():
    p = DeleteProperties(
        mode=WriteMode.COPY_ON_WRITE,
        isolation_level=IsolationLevel.SERIALIZABLE,
        distribution_mode=DistributionMode.RANGE,
        format_default="parquet",
        target_file_size_bytes=67108864,
        parquet=ParquetProperties(compression_codec="zstd"),
    )
    assert p.mode == WriteMode.COPY_ON_WRITE
    assert p.format_default == "parquet"
    assert p.parquet is not None
    assert p.parquet.compression_codec == "zstd"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/catalog/table_properties/test_operation_properties.py tests/application/domain/model/catalog/table_properties/test_delete_properties.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the implementation files**

Create `application/domain/model/catalog/table_properties/operation_properties.py`:

```python
"""Define the OperationProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode
from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel
from application.domain.model.catalog.table_properties.write_mode import WriteMode


@dataclass(frozen=True)
class OperationProperties(ValueObject):
    """Per-operation write properties shared by merge and update."""

    mode: WriteMode | None = None
    isolation_level: IsolationLevel | None = None
    distribution_mode: DistributionMode | None = None
```

Create `application/domain/model/catalog/table_properties/delete_properties.py`:

```python
"""Define the DeleteProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode
from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel
from application.domain.model.catalog.table_properties.parquet_properties import ParquetProperties
from application.domain.model.catalog.table_properties.write_mode import WriteMode


@dataclass(frozen=True)
class DeleteProperties(ValueObject):
    """Delete operation properties with additional format and parquet settings."""

    mode: WriteMode | None = None
    isolation_level: IsolationLevel | None = None
    distribution_mode: DistributionMode | None = None
    format_default: str | None = None
    target_file_size_bytes: int | None = None
    parquet: ParquetProperties | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/catalog/table_properties/ -v`

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/application/domain/model/catalog/table_properties/ src/table-maintenance/backend/tests/application/domain/model/catalog/table_properties/
git commit -m "feat(catalog): add OperationProperties and DeleteProperties value objects"
```

---

## Task 4: Composite VOs — WriteProperties, ReadProperties, TableProperties + __init__.py

**Files:**
- Create: `application/domain/model/catalog/table_properties/write_properties.py`
- Create: `application/domain/model/catalog/table_properties/read_properties.py`
- Create: `application/domain/model/catalog/table_properties/table_properties.py`
- Create: `application/domain/model/catalog/table_properties/__init__.py`
- Test: `tests/application/domain/model/catalog/table_properties/test_table_properties.py`

- [ ] **Step 1: Write the failing test**

Create `tests/application/domain/model/catalog/table_properties/test_table_properties.py`:

```python
"""Test the TableProperties composite value object."""

from __future__ import annotations

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.table_properties import TableProperties
from application.domain.model.catalog.table_properties.write_properties import WriteProperties
from application.domain.model.catalog.table_properties.read_properties import ReadProperties
from application.domain.model.catalog.table_properties.operation_properties import OperationProperties
from application.domain.model.catalog.table_properties.delete_properties import DeleteProperties
from application.domain.model.catalog.table_properties.parquet_properties import ParquetProperties
from application.domain.model.catalog.table_properties.split_properties import SplitProperties
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode


def test_table_properties_is_value_object():
    assert issubclass(TableProperties, ValueObject)


def test_all_defaults_none():
    p = TableProperties()
    assert p.format_version is None
    assert p.write is None
    assert p.read is None


def test_full_nested_structure():
    p = TableProperties(
        format_version=2,
        write=WriteProperties(
            merge=OperationProperties(mode=WriteMode.MERGE_ON_READ),
            update=OperationProperties(mode=WriteMode.COPY_ON_WRITE),
            delete=DeleteProperties(
                mode=WriteMode.COPY_ON_WRITE,
                parquet=ParquetProperties(compression_codec="zstd"),
            ),
            distribution_mode=DistributionMode.HASH,
            target_file_size_bytes=536870912,
            upsert_enabled=False,
        ),
        read=ReadProperties(
            split=SplitProperties(size=134217728),
        ),
    )
    assert p.format_version == 2
    assert p.write.merge.mode == WriteMode.MERGE_ON_READ
    assert p.write.delete.parquet.compression_codec == "zstd"
    assert p.write.distribution_mode == DistributionMode.HASH
    assert p.read.split.size == 134217728


def test_package_reexports():
    """Verify __init__.py re-exports key symbols."""
    from application.domain.model.catalog.table_properties import (
        TableProperties,
        WriteProperties,
        ReadProperties,
        WriteMode,
        DistributionMode,
        IsolationLevel,
        OperationProperties,
        DeleteProperties,
        ParquetProperties,
    )
    assert TableProperties is not None
    assert WriteMode.COPY_ON_WRITE == "copy-on-write"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/catalog/table_properties/test_table_properties.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create the composite VOs and __init__.py**

Create `application/domain/model/catalog/table_properties/write_properties.py`:

```python
"""Define the WriteProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.commit_properties import CommitProperties
from application.domain.model.catalog.table_properties.delete_properties import DeleteProperties
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode
from application.domain.model.catalog.table_properties.format_properties import FormatProperties
from application.domain.model.catalog.table_properties.manifest_properties import ManifestProperties
from application.domain.model.catalog.table_properties.metadata_properties import MetadataProperties
from application.domain.model.catalog.table_properties.metrics_properties import MetricsProperties
from application.domain.model.catalog.table_properties.operation_properties import OperationProperties
from application.domain.model.catalog.table_properties.parquet_properties import ParquetProperties


@dataclass(frozen=True)
class WriteProperties(ValueObject):
    """All write-related table properties."""

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
```

Create `application/domain/model/catalog/table_properties/read_properties.py`:

```python
"""Define the ReadProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.read_orc_properties import ReadOrcProperties
from application.domain.model.catalog.table_properties.read_parquet_properties import ReadParquetProperties
from application.domain.model.catalog.table_properties.split_properties import SplitProperties


@dataclass(frozen=True)
class ReadProperties(ValueObject):
    """All read-related table properties."""

    split: SplitProperties | None = None
    parquet: ReadParquetProperties | None = None
    orc: ReadOrcProperties | None = None
```

Create `application/domain/model/catalog/table_properties/table_properties.py`:

```python
"""Define the TableProperties value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject
from application.domain.model.catalog.table_properties.read_properties import ReadProperties
from application.domain.model.catalog.table_properties.write_properties import WriteProperties


@dataclass(frozen=True)
class TableProperties(ValueObject):
    """Top-level container for all Iceberg table properties."""

    format_version: int | None = None
    write: WriteProperties | None = None
    read: ReadProperties | None = None
```

Create `application/domain/model/catalog/table_properties/__init__.py`:

```python
"""Table properties domain model — nested value objects for Iceberg table configuration."""

from application.domain.model.catalog.table_properties.commit_properties import CommitProperties
from application.domain.model.catalog.table_properties.delete_properties import DeleteProperties
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode
from application.domain.model.catalog.table_properties.format_properties import FormatProperties
from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel
from application.domain.model.catalog.table_properties.manifest_properties import ManifestProperties
from application.domain.model.catalog.table_properties.metadata_properties import MetadataProperties
from application.domain.model.catalog.table_properties.metrics_properties import MetricsProperties
from application.domain.model.catalog.table_properties.operation_properties import OperationProperties
from application.domain.model.catalog.table_properties.parquet_properties import ParquetProperties
from application.domain.model.catalog.table_properties.read_orc_properties import ReadOrcProperties
from application.domain.model.catalog.table_properties.read_parquet_properties import ReadParquetProperties
from application.domain.model.catalog.table_properties.read_properties import ReadProperties
from application.domain.model.catalog.table_properties.split_properties import SplitProperties
from application.domain.model.catalog.table_properties.table_properties import TableProperties
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.write_properties import WriteProperties

__all__ = [
    "CommitProperties",
    "DeleteProperties",
    "DistributionMode",
    "FormatProperties",
    "IsolationLevel",
    "ManifestProperties",
    "MetadataProperties",
    "MetricsProperties",
    "OperationProperties",
    "ParquetProperties",
    "ReadOrcProperties",
    "ReadParquetProperties",
    "ReadProperties",
    "SplitProperties",
    "TableProperties",
    "WriteMode",
    "WriteProperties",
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/catalog/table_properties/ -v`

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/application/domain/model/catalog/table_properties/ src/table-maintenance/backend/tests/application/domain/model/catalog/table_properties/
git commit -m "feat(catalog): add composite WriteProperties, ReadProperties, TableProperties"
```

---

## Task 5: dict_to_table_properties converter

**Files:**
- Create: `adapter/outbound/catalog/dict_to_table_properties.py`
- Test: `tests/adapter/outbound/catalog/test_dict_to_table_properties.py`

- [ ] **Step 1: Write the failing test**

Create `tests/adapter/outbound/catalog/test_dict_to_table_properties.py`:

```python
"""Test dict_to_table_properties converter."""

from __future__ import annotations

from adapter.outbound.catalog.dict_to_table_properties import dict_to_table_properties
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode
from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel


def test_empty_dict():
    result = dict_to_table_properties({})
    assert result.format_version is None
    assert result.write is None
    assert result.read is None


def test_format_version():
    result = dict_to_table_properties({"format-version": "2"})
    assert result.format_version == 2


def test_write_merge_mode():
    result = dict_to_table_properties({"write.merge.mode": "merge-on-read"})
    assert result.write.merge.mode == WriteMode.MERGE_ON_READ


def test_write_update_mode():
    result = dict_to_table_properties({"write.update.mode": "copy-on-write"})
    assert result.write.update.mode == WriteMode.COPY_ON_WRITE


def test_write_delete_mode():
    result = dict_to_table_properties({
        "write.delete.mode": "copy-on-write",
        "write.delete.isolation-level": "serializable",
        "write.delete.distribution-mode": "hash",
    })
    assert result.write.delete.mode == WriteMode.COPY_ON_WRITE
    assert result.write.delete.isolation_level == IsolationLevel.SERIALIZABLE
    assert result.write.delete.distribution_mode == DistributionMode.HASH


def test_write_delete_parquet():
    result = dict_to_table_properties({
        "write.delete.parquet.compression-codec": "zstd",
        "write.delete.parquet.row-group-size-bytes": "134217728",
    })
    assert result.write.delete.parquet.compression_codec == "zstd"
    assert result.write.delete.parquet.row_group_size_bytes == 134217728


def test_write_delete_format_and_size():
    result = dict_to_table_properties({
        "write.delete.format.default": "parquet",
        "write.delete.target-file-size-bytes": "67108864",
    })
    assert result.write.delete.format_default == "parquet"
    assert result.write.delete.target_file_size_bytes == 67108864


def test_write_distribution_mode():
    result = dict_to_table_properties({"write.distribution-mode": "range"})
    assert result.write.distribution_mode == DistributionMode.RANGE


def test_write_format_default():
    result = dict_to_table_properties({"write.format.default": "parquet"})
    assert result.write.format.default == "parquet"


def test_write_parquet_settings():
    result = dict_to_table_properties({
        "write.parquet.compression-codec": "snappy",
        "write.parquet.compression-level": "5",
        "write.parquet.row-group-size-bytes": "134217728",
        "write.parquet.page-size-bytes": "1048576",
        "write.parquet.dict-size-bytes": "2097152",
    })
    assert result.write.parquet.compression_codec == "snappy"
    assert result.write.parquet.compression_level == 5
    assert result.write.parquet.row_group_size_bytes == 134217728
    assert result.write.parquet.page_size_bytes == 1048576
    assert result.write.parquet.dict_size_bytes == 2097152


def test_write_target_file_size():
    result = dict_to_table_properties({"write.target-file-size-bytes": "536870912"})
    assert result.write.target_file_size_bytes == 536870912


def test_write_manifest():
    result = dict_to_table_properties({
        "write.manifest.target-size-bytes": "8388608",
        "write.manifest.min-merge-count": "4",
        "write.manifest.merge.enabled": "true",
    })
    assert result.write.manifest.target_size_bytes == 8388608
    assert result.write.manifest.min_merge_count == 4
    assert result.write.manifest.merge_enabled is True


def test_write_metadata():
    result = dict_to_table_properties({
        "write.metadata.compression-codec": "gzip",
        "write.metadata.delete-after-commit.enabled": "false",
        "write.metadata.previous-versions-max": "100",
    })
    assert result.write.metadata.compression_codec == "gzip"
    assert result.write.metadata.delete_after_commit_enabled is False
    assert result.write.metadata.previous_versions_max == 100


def test_write_commit():
    result = dict_to_table_properties({
        "write.commit.num-retries": "3",
        "write.commit.retry.min-wait-ms": "100",
        "write.commit.retry.max-wait-ms": "60000",
        "write.commit.retry.total-timeout-ms": "600000",
    })
    assert result.write.commit.num_retries == 3
    assert result.write.commit.retry_min_wait_ms == 100
    assert result.write.commit.retry_max_wait_ms == 60000
    assert result.write.commit.total_retry_time_ms == 600000


def test_write_metrics():
    result = dict_to_table_properties({"write.metrics.mode": "truncate(16)"})
    assert result.write.metrics.default_mode == "truncate(16)"


def test_write_flags():
    result = dict_to_table_properties({
        "write.upsert.enabled": "true",
        "write.wap.enabled": "false",
        "write.object-storage.enabled": "true",
    })
    assert result.write.upsert_enabled is True
    assert result.write.wap_enabled is False
    assert result.write.object_storage_enabled is True


def test_read_split():
    result = dict_to_table_properties({
        "read.split.planning.size": "134217728",
        "read.split.planning.lookback": "10",
        "read.split.planning.open-file-cost": "4194304",
    })
    assert result.read.split.size == 134217728
    assert result.read.split.lookback == 10
    assert result.read.split.open_file_cost == 4194304


def test_read_parquet():
    result = dict_to_table_properties({
        "read.parquet.vectorization.enabled": "true",
        "read.parquet.batch-size": "128",
    })
    assert result.read.parquet.vectorization_enabled is True
    assert result.read.parquet.batch_size == 128


def test_read_orc():
    result = dict_to_table_properties({
        "read.orc.vectorization.enabled": "false",
        "read.orc.batch-size": "256",
    })
    assert result.read.orc.vectorization_enabled is False
    assert result.read.orc.batch_size == 256


def test_none_groups_when_no_keys_present():
    """Groups that have zero keys should be None, not empty VOs."""
    result = dict_to_table_properties({"format-version": "2"})
    assert result.write is None
    assert result.read is None


def test_nested_none_groups():
    """Sub-groups that have zero keys should be None."""
    result = dict_to_table_properties({"write.merge.mode": "merge-on-read"})
    assert result.write.merge.mode == WriteMode.MERGE_ON_READ
    assert result.write.update is None
    assert result.write.delete is None
    assert result.write.parquet is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/catalog/test_dict_to_table_properties.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the converter**

Create `adapter/outbound/catalog/dict_to_table_properties.py`:

```python
"""Convert a raw Iceberg properties dict to a typed TableProperties value object."""

from __future__ import annotations

from enum import StrEnum

from application.domain.model.catalog.table_properties.commit_properties import CommitProperties
from application.domain.model.catalog.table_properties.delete_properties import DeleteProperties
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode
from application.domain.model.catalog.table_properties.format_properties import FormatProperties
from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel
from application.domain.model.catalog.table_properties.manifest_properties import ManifestProperties
from application.domain.model.catalog.table_properties.metadata_properties import MetadataProperties
from application.domain.model.catalog.table_properties.metrics_properties import MetricsProperties
from application.domain.model.catalog.table_properties.operation_properties import OperationProperties
from application.domain.model.catalog.table_properties.parquet_properties import ParquetProperties
from application.domain.model.catalog.table_properties.read_orc_properties import ReadOrcProperties
from application.domain.model.catalog.table_properties.read_parquet_properties import ReadParquetProperties
from application.domain.model.catalog.table_properties.read_properties import ReadProperties
from application.domain.model.catalog.table_properties.split_properties import SplitProperties
from application.domain.model.catalog.table_properties.table_properties import TableProperties
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.write_properties import WriteProperties


def dict_to_table_properties(raw: dict[str, str]) -> TableProperties:
    """Convert a raw Iceberg properties dict to a typed TableProperties."""
    write = _build_write(raw)
    read = _build_read(raw)
    return TableProperties(
        format_version=_int(raw.get("format-version")),
        write=write,
        read=read,
    )


# --- Write ---


def _build_write(raw: dict[str, str]) -> WriteProperties | None:
    merge = _build_operation(raw, "write.merge")
    update = _build_operation(raw, "write.update")
    delete = _build_delete(raw)
    distribution_mode = _enum(DistributionMode, raw.get("write.distribution-mode"))
    fmt = _build_format(raw)
    parquet = _build_parquet(raw, "write.parquet")
    target_file_size_bytes = _int(raw.get("write.target-file-size-bytes"))
    manifest = _build_manifest(raw)
    metadata = _build_metadata(raw)
    commit = _build_commit(raw)
    metrics = _build_metrics(raw)
    upsert_enabled = _bool(raw.get("write.upsert.enabled"))
    wap_enabled = _bool(raw.get("write.wap.enabled"))
    object_storage_enabled = _bool(raw.get("write.object-storage.enabled"))

    if all(
        v is None
        for v in (
            merge, update, delete, distribution_mode, fmt, parquet,
            target_file_size_bytes, manifest, metadata, commit, metrics,
            upsert_enabled, wap_enabled, object_storage_enabled,
        )
    ):
        return None

    return WriteProperties(
        merge=merge,
        update=update,
        delete=delete,
        distribution_mode=distribution_mode,
        format=fmt,
        parquet=parquet,
        target_file_size_bytes=target_file_size_bytes,
        manifest=manifest,
        metadata=metadata,
        commit=commit,
        metrics=metrics,
        upsert_enabled=upsert_enabled,
        wap_enabled=wap_enabled,
        object_storage_enabled=object_storage_enabled,
    )


def _build_operation(raw: dict[str, str], prefix: str) -> OperationProperties | None:
    mode = _enum(WriteMode, raw.get(f"{prefix}.mode"))
    isolation = _enum(IsolationLevel, raw.get(f"{prefix}.isolation-level"))
    dist = _enum(DistributionMode, raw.get(f"{prefix}.distribution-mode"))
    if all(v is None for v in (mode, isolation, dist)):
        return None
    return OperationProperties(mode=mode, isolation_level=isolation, distribution_mode=dist)


def _build_delete(raw: dict[str, str]) -> DeleteProperties | None:
    mode = _enum(WriteMode, raw.get("write.delete.mode"))
    isolation = _enum(IsolationLevel, raw.get("write.delete.isolation-level"))
    dist = _enum(DistributionMode, raw.get("write.delete.distribution-mode"))
    format_default = raw.get("write.delete.format.default")
    target = _int(raw.get("write.delete.target-file-size-bytes"))
    parquet = _build_parquet(raw, "write.delete.parquet")
    if all(v is None for v in (mode, isolation, dist, format_default, target, parquet)):
        return None
    return DeleteProperties(
        mode=mode,
        isolation_level=isolation,
        distribution_mode=dist,
        format_default=format_default,
        target_file_size_bytes=target,
        parquet=parquet,
    )


def _build_parquet(raw: dict[str, str], prefix: str) -> ParquetProperties | None:
    codec = raw.get(f"{prefix}.compression-codec")
    level = _int(raw.get(f"{prefix}.compression-level"))
    row_group = _int(raw.get(f"{prefix}.row-group-size-bytes"))
    page = _int(raw.get(f"{prefix}.page-size-bytes"))
    dict_size = _int(raw.get(f"{prefix}.dict-size-bytes"))
    if all(v is None for v in (codec, level, row_group, page, dict_size)):
        return None
    return ParquetProperties(
        compression_codec=codec,
        compression_level=level,
        row_group_size_bytes=row_group,
        page_size_bytes=page,
        dict_size_bytes=dict_size,
    )


def _build_format(raw: dict[str, str]) -> FormatProperties | None:
    default = raw.get("write.format.default")
    if default is None:
        return None
    return FormatProperties(default=default)


def _build_manifest(raw: dict[str, str]) -> ManifestProperties | None:
    target = _int(raw.get("write.manifest.target-size-bytes"))
    min_merge = _int(raw.get("write.manifest.min-merge-count"))
    merge_enabled = _bool(raw.get("write.manifest.merge.enabled"))
    if all(v is None for v in (target, min_merge, merge_enabled)):
        return None
    return ManifestProperties(
        target_size_bytes=target, min_merge_count=min_merge, merge_enabled=merge_enabled,
    )


def _build_metadata(raw: dict[str, str]) -> MetadataProperties | None:
    codec = raw.get("write.metadata.compression-codec")
    delete_after = _bool(raw.get("write.metadata.delete-after-commit.enabled"))
    prev_max = _int(raw.get("write.metadata.previous-versions-max"))
    if all(v is None for v in (codec, delete_after, prev_max)):
        return None
    return MetadataProperties(
        compression_codec=codec, delete_after_commit_enabled=delete_after, previous_versions_max=prev_max,
    )


def _build_commit(raw: dict[str, str]) -> CommitProperties | None:
    retries = _int(raw.get("write.commit.num-retries"))
    min_wait = _int(raw.get("write.commit.retry.min-wait-ms"))
    max_wait = _int(raw.get("write.commit.retry.max-wait-ms"))
    total = _int(raw.get("write.commit.retry.total-timeout-ms"))
    if all(v is None for v in (retries, min_wait, max_wait, total)):
        return None
    return CommitProperties(
        num_retries=retries, retry_min_wait_ms=min_wait, retry_max_wait_ms=max_wait, total_retry_time_ms=total,
    )


def _build_metrics(raw: dict[str, str]) -> MetricsProperties | None:
    mode = raw.get("write.metrics.mode")
    if mode is None:
        return None
    return MetricsProperties(default_mode=mode)


# --- Read ---


def _build_read(raw: dict[str, str]) -> ReadProperties | None:
    split = _build_split(raw)
    parquet = _build_read_parquet(raw)
    orc = _build_read_orc(raw)
    if all(v is None for v in (split, parquet, orc)):
        return None
    return ReadProperties(split=split, parquet=parquet, orc=orc)


def _build_split(raw: dict[str, str]) -> SplitProperties | None:
    size = _int(raw.get("read.split.planning.size"))
    lookback = _int(raw.get("read.split.planning.lookback"))
    cost = _int(raw.get("read.split.planning.open-file-cost"))
    if all(v is None for v in (size, lookback, cost)):
        return None
    return SplitProperties(size=size, lookback=lookback, open_file_cost=cost)


def _build_read_parquet(raw: dict[str, str]) -> ReadParquetProperties | None:
    vec = _bool(raw.get("read.parquet.vectorization.enabled"))
    batch = _int(raw.get("read.parquet.batch-size"))
    if all(v is None for v in (vec, batch)):
        return None
    return ReadParquetProperties(vectorization_enabled=vec, batch_size=batch)


def _build_read_orc(raw: dict[str, str]) -> ReadOrcProperties | None:
    vec = _bool(raw.get("read.orc.vectorization.enabled"))
    batch = _int(raw.get("read.orc.batch-size"))
    if all(v is None for v in (vec, batch)):
        return None
    return ReadOrcProperties(vectorization_enabled=vec, batch_size=batch)


# --- Helpers ---


def _int(v: str | None) -> int | None:
    return int(v) if v is not None else None


def _bool(v: str | None) -> bool | None:
    return v.lower() == "true" if v is not None else None


def _enum[T: StrEnum](cls: type[T], v: str | None) -> T | None:
    return cls(v) if v is not None else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/catalog/test_dict_to_table_properties.py -v`

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/adapter/outbound/catalog/dict_to_table_properties.py src/table-maintenance/backend/tests/adapter/outbound/catalog/test_dict_to_table_properties.py
git commit -m "feat(catalog): add dict_to_table_properties converter"
```

---

## Task 6: table_properties_to_dict converter

**Files:**
- Create: `adapter/outbound/catalog/table_properties_to_dict.py`
- Test: `tests/adapter/outbound/catalog/test_table_properties_to_dict.py`

- [ ] **Step 1: Write the failing test**

Create `tests/adapter/outbound/catalog/test_table_properties_to_dict.py`:

```python
"""Test table_properties_to_dict converter."""

from __future__ import annotations

from adapter.outbound.catalog.table_properties_to_dict import table_properties_to_dict
from application.domain.model.catalog.table_properties.commit_properties import CommitProperties
from application.domain.model.catalog.table_properties.delete_properties import DeleteProperties
from application.domain.model.catalog.table_properties.distribution_mode import DistributionMode
from application.domain.model.catalog.table_properties.format_properties import FormatProperties
from application.domain.model.catalog.table_properties.isolation_level import IsolationLevel
from application.domain.model.catalog.table_properties.manifest_properties import ManifestProperties
from application.domain.model.catalog.table_properties.metadata_properties import MetadataProperties
from application.domain.model.catalog.table_properties.metrics_properties import MetricsProperties
from application.domain.model.catalog.table_properties.operation_properties import OperationProperties
from application.domain.model.catalog.table_properties.parquet_properties import ParquetProperties
from application.domain.model.catalog.table_properties.read_orc_properties import ReadOrcProperties
from application.domain.model.catalog.table_properties.read_parquet_properties import ReadParquetProperties
from application.domain.model.catalog.table_properties.read_properties import ReadProperties
from application.domain.model.catalog.table_properties.split_properties import SplitProperties
from application.domain.model.catalog.table_properties.table_properties import TableProperties
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_properties.write_properties import WriteProperties


def test_empty_properties():
    result = table_properties_to_dict(TableProperties())
    assert result == {}


def test_format_version():
    result = table_properties_to_dict(TableProperties(format_version=2))
    assert result == {"format-version": "2"}


def test_write_merge_mode():
    result = table_properties_to_dict(TableProperties(
        write=WriteProperties(
            merge=OperationProperties(mode=WriteMode.MERGE_ON_READ),
        ),
    ))
    assert result["write.merge.mode"] == "merge-on-read"


def test_write_delete_with_parquet():
    result = table_properties_to_dict(TableProperties(
        write=WriteProperties(
            delete=DeleteProperties(
                mode=WriteMode.COPY_ON_WRITE,
                format_default="parquet",
                target_file_size_bytes=67108864,
                parquet=ParquetProperties(compression_codec="zstd"),
            ),
        ),
    ))
    assert result["write.delete.mode"] == "copy-on-write"
    assert result["write.delete.format.default"] == "parquet"
    assert result["write.delete.target-file-size-bytes"] == "67108864"
    assert result["write.delete.parquet.compression-codec"] == "zstd"


def test_write_flags():
    result = table_properties_to_dict(TableProperties(
        write=WriteProperties(
            upsert_enabled=True,
            wap_enabled=False,
        ),
    ))
    assert result["write.upsert.enabled"] == "true"
    assert result["write.wap.enabled"] == "false"


def test_read_split():
    result = table_properties_to_dict(TableProperties(
        read=ReadProperties(
            split=SplitProperties(size=134217728, lookback=10),
        ),
    ))
    assert result["read.split.planning.size"] == "134217728"
    assert result["read.split.planning.lookback"] == "10"


def test_skips_none_values():
    """None fields should not appear in the output dict."""
    result = table_properties_to_dict(TableProperties(
        write=WriteProperties(
            merge=OperationProperties(mode=WriteMode.MERGE_ON_READ),
        ),
    ))
    assert "write.merge.isolation-level" not in result
    assert "write.merge.distribution-mode" not in result


def test_roundtrip():
    """dict -> TableProperties -> dict should preserve all values."""
    from adapter.outbound.catalog.dict_to_table_properties import dict_to_table_properties

    original = {
        "format-version": "2",
        "write.merge.mode": "merge-on-read",
        "write.delete.mode": "copy-on-write",
        "write.delete.parquet.compression-codec": "zstd",
        "write.distribution-mode": "hash",
        "write.format.default": "parquet",
        "write.parquet.compression-codec": "snappy",
        "write.target-file-size-bytes": "536870912",
        "write.upsert.enabled": "true",
        "read.split.planning.size": "134217728",
        "read.parquet.vectorization.enabled": "true",
    }
    props = dict_to_table_properties(original)
    result = table_properties_to_dict(props)
    assert result == original
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/catalog/test_table_properties_to_dict.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement the converter**

Create `adapter/outbound/catalog/table_properties_to_dict.py`:

```python
"""Convert a typed TableProperties value object to a raw Iceberg properties dict."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.domain.model.catalog.table_properties.delete_properties import DeleteProperties
    from application.domain.model.catalog.table_properties.table_properties import TableProperties


def table_properties_to_dict(props: TableProperties) -> dict[str, str]:
    """Flatten a TableProperties VO to an Iceberg-compatible dict[str, str]."""
    result: dict[str, str] = {}

    if props.format_version is not None:
        result["format-version"] = str(props.format_version)

    if props.write is not None:
        w = props.write
        _put_operation(result, "write.merge", w.merge)
        _put_operation(result, "write.update", w.update)
        _put_delete(result, w.delete)
        _put(result, "write.distribution-mode", w.distribution_mode)
        if w.format is not None:
            _put(result, "write.format.default", w.format.default)
        _put_parquet(result, "write.parquet", w.parquet)
        _put(result, "write.target-file-size-bytes", w.target_file_size_bytes)
        if w.manifest is not None:
            _put(result, "write.manifest.target-size-bytes", w.manifest.target_size_bytes)
            _put(result, "write.manifest.min-merge-count", w.manifest.min_merge_count)
            _put_bool(result, "write.manifest.merge.enabled", w.manifest.merge_enabled)
        if w.metadata is not None:
            _put(result, "write.metadata.compression-codec", w.metadata.compression_codec)
            _put_bool(result, "write.metadata.delete-after-commit.enabled", w.metadata.delete_after_commit_enabled)
            _put(result, "write.metadata.previous-versions-max", w.metadata.previous_versions_max)
        if w.commit is not None:
            _put(result, "write.commit.num-retries", w.commit.num_retries)
            _put(result, "write.commit.retry.min-wait-ms", w.commit.retry_min_wait_ms)
            _put(result, "write.commit.retry.max-wait-ms", w.commit.retry_max_wait_ms)
            _put(result, "write.commit.retry.total-timeout-ms", w.commit.total_retry_time_ms)
        if w.metrics is not None:
            _put(result, "write.metrics.mode", w.metrics.default_mode)
        _put_bool(result, "write.upsert.enabled", w.upsert_enabled)
        _put_bool(result, "write.wap.enabled", w.wap_enabled)
        _put_bool(result, "write.object-storage.enabled", w.object_storage_enabled)

    if props.read is not None:
        r = props.read
        if r.split is not None:
            _put(result, "read.split.planning.size", r.split.size)
            _put(result, "read.split.planning.lookback", r.split.lookback)
            _put(result, "read.split.planning.open-file-cost", r.split.open_file_cost)
        if r.parquet is not None:
            _put_bool(result, "read.parquet.vectorization.enabled", r.parquet.vectorization_enabled)
            _put(result, "read.parquet.batch-size", r.parquet.batch_size)
        if r.orc is not None:
            _put_bool(result, "read.orc.vectorization.enabled", r.orc.vectorization_enabled)
            _put(result, "read.orc.batch-size", r.orc.batch_size)

    return result


def _put_operation(result: dict[str, str], prefix: str, op: object | None) -> None:
    if op is None:
        return
    _put(result, f"{prefix}.mode", getattr(op, "mode", None))
    _put(result, f"{prefix}.isolation-level", getattr(op, "isolation_level", None))
    _put(result, f"{prefix}.distribution-mode", getattr(op, "distribution_mode", None))


def _put_delete(result: dict[str, str], d: DeleteProperties | None) -> None:
    if d is None:
        return
    _put(result, "write.delete.mode", d.mode)
    _put(result, "write.delete.isolation-level", d.isolation_level)
    _put(result, "write.delete.distribution-mode", d.distribution_mode)
    _put(result, "write.delete.format.default", d.format_default)
    _put(result, "write.delete.target-file-size-bytes", d.target_file_size_bytes)
    _put_parquet(result, "write.delete.parquet", d.parquet)


def _put_parquet(result: dict[str, str], prefix: str, p: object | None) -> None:
    if p is None:
        return
    _put(result, f"{prefix}.compression-codec", getattr(p, "compression_codec", None))
    _put(result, f"{prefix}.compression-level", getattr(p, "compression_level", None))
    _put(result, f"{prefix}.row-group-size-bytes", getattr(p, "row_group_size_bytes", None))
    _put(result, f"{prefix}.page-size-bytes", getattr(p, "page_size_bytes", None))
    _put(result, f"{prefix}.dict-size-bytes", getattr(p, "dict_size_bytes", None))


def _put(result: dict[str, str], key: str, value: object | None) -> None:
    if value is not None:
        result[key] = str(value)


def _put_bool(result: dict[str, str], key: str, value: bool | None) -> None:
    if value is not None:
        result[key] = "true" if value else "false"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/catalog/test_table_properties_to_dict.py -v`

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/adapter/outbound/catalog/table_properties_to_dict.py src/table-maintenance/backend/tests/adapter/outbound/catalog/test_table_properties_to_dict.py
git commit -m "feat(catalog): add table_properties_to_dict converter"
```

---

## Task 7: Wire Table aggregate + update existing code

**Files:**
- Modify: `application/domain/model/catalog/table.py`
- Modify: `application/domain/model/catalog/__init__.py`
- Modify: `adapter/outbound/catalog/read_catalog_iceberg_gateway.py`
- Modify: `application/service/catalog/get_table.py`
- Modify: `tests/application/domain/model/catalog/test_table.py`
- Modify: `tests/application/service/catalog/test_get_table.py`
- Modify: `tests/adapter/outbound/catalog/test_read_catalog_iceberg_gateway.py`

- [ ] **Step 1: Update Table aggregate — change `properties` type**

In `application/domain/model/catalog/table.py`, replace `properties: dict[str, str]` with `properties: TableProperties`:

```python
"""Define the Table aggregate root."""

from __future__ import annotations

from dataclasses import dataclass

from base.aggregate_root import AggregateRoot
from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_properties.table_properties import TableProperties
from application.domain.model.catalog.table_schema import TableSchema
from application.domain.model.catalog.tag import Tag


@dataclass(eq=False)
class Table(AggregateRoot[TableId]):
    """The Table aggregate root — Iceberg table metadata (analogous to a Git repository)."""

    id: TableId
    namespace: str
    name: str
    location: str
    current_snapshot_id: int | None
    schema: TableSchema
    snapshots: tuple[Snapshot, ...]
    branches: tuple[Branch, ...]
    tags: tuple[Tag, ...]
    properties: TableProperties
```

- [ ] **Step 2: Update catalog __init__.py with new re-exports**

In `application/domain/model/catalog/__init__.py`, add `TableProperties` and the key enums:

```python
"""Catalog domain model — Table aggregate root and related types."""

from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.retention_policy import RetentionPolicy
from application.domain.model.catalog.schema_field import SchemaField
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.snapshot_summary import SnapshotSummary
from application.domain.model.catalog.table import Table
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_properties import (
    DistributionMode,
    IsolationLevel,
    TableProperties,
    WriteMode,
)
from application.domain.model.catalog.table_schema import TableSchema
from application.domain.model.catalog.tag import Tag

__all__ = [
    "Branch",
    "BranchId",
    "DistributionMode",
    "IsolationLevel",
    "RetentionPolicy",
    "SchemaField",
    "Snapshot",
    "SnapshotSummary",
    "Table",
    "TableId",
    "TableProperties",
    "TableSchema",
    "Tag",
    "WriteMode",
]
```

- [ ] **Step 3: Update ReadCatalogIcebergGateway to use dict_to_table_properties**

In `adapter/outbound/catalog/read_catalog_iceberg_gateway.py`, change line 108 from `properties=dict(tbl.metadata.properties)` to use the converter. Add the import at the top:

```python
from adapter.outbound.catalog.dict_to_table_properties import dict_to_table_properties
```

Replace line 108:

```python
            properties=dict_to_table_properties(dict(tbl.metadata.properties)),
```

- [ ] **Step 4: Update GetTableService to convert back to dict for output**

In `application/service/catalog/get_table.py`, the service needs to convert `TableProperties` back to `dict[str, str]` for the output. However, the service layer cannot import from adapter. The `table_properties_to_dict` lives in the adapter layer.

Instead, the conversion should happen in the adapter (web endpoint) or we need to move the converter to the application layer. Since the output DTO uses `dict[str, str]` and the service constructs it, the simplest approach is: the service imports `table_properties_to_dict` — but wait, that's in the adapter layer.

**Solution:** Move `table_properties_to_dict` to the application service layer as a private helper in `get_table.py`, or create `application/service/catalog/_table_properties_serializer.py`. But actually, the cleanest approach per our architecture is to keep the converter in the adapter, and have the web adapter do the conversion.

**Revised approach:** Change `GetTableOutput.properties` from `dict[str, str]` to `dict[str, str]` but have the web adapter call the converter. Actually, the service needs to produce the output. Let's keep the converter function in the service layer instead.

Create `application/service/catalog/table_properties_serializer.py`:

```python
"""Serialize TableProperties to a flat dict for output DTOs."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from application.domain.model.catalog.table_properties.delete_properties import DeleteProperties
    from application.domain.model.catalog.table_properties.table_properties import TableProperties


def table_properties_to_dict(props: TableProperties) -> dict[str, str]:
    """Flatten a TableProperties VO to a dict[str, str] for output DTOs."""
    result: dict[str, str] = {}

    if props.format_version is not None:
        result["format-version"] = str(props.format_version)

    if props.write is not None:
        w = props.write
        _put_operation(result, "write.merge", w.merge)
        _put_operation(result, "write.update", w.update)
        _put_delete(result, w.delete)
        _put(result, "write.distribution-mode", w.distribution_mode)
        if w.format is not None:
            _put(result, "write.format.default", w.format.default)
        _put_parquet(result, "write.parquet", w.parquet)
        _put(result, "write.target-file-size-bytes", w.target_file_size_bytes)
        if w.manifest is not None:
            _put(result, "write.manifest.target-size-bytes", w.manifest.target_size_bytes)
            _put(result, "write.manifest.min-merge-count", w.manifest.min_merge_count)
            _put_bool(result, "write.manifest.merge.enabled", w.manifest.merge_enabled)
        if w.metadata is not None:
            _put(result, "write.metadata.compression-codec", w.metadata.compression_codec)
            _put_bool(result, "write.metadata.delete-after-commit.enabled", w.metadata.delete_after_commit_enabled)
            _put(result, "write.metadata.previous-versions-max", w.metadata.previous_versions_max)
        if w.commit is not None:
            _put(result, "write.commit.num-retries", w.commit.num_retries)
            _put(result, "write.commit.retry.min-wait-ms", w.commit.retry_min_wait_ms)
            _put(result, "write.commit.retry.max-wait-ms", w.commit.retry_max_wait_ms)
            _put(result, "write.commit.retry.total-timeout-ms", w.commit.total_retry_time_ms)
        if w.metrics is not None:
            _put(result, "write.metrics.mode", w.metrics.default_mode)
        _put_bool(result, "write.upsert.enabled", w.upsert_enabled)
        _put_bool(result, "write.wap.enabled", w.wap_enabled)
        _put_bool(result, "write.object-storage.enabled", w.object_storage_enabled)

    if props.read is not None:
        r = props.read
        if r.split is not None:
            _put(result, "read.split.planning.size", r.split.size)
            _put(result, "read.split.planning.lookback", r.split.lookback)
            _put(result, "read.split.planning.open-file-cost", r.split.open_file_cost)
        if r.parquet is not None:
            _put_bool(result, "read.parquet.vectorization.enabled", r.parquet.vectorization_enabled)
            _put(result, "read.parquet.batch-size", r.parquet.batch_size)
        if r.orc is not None:
            _put_bool(result, "read.orc.vectorization.enabled", r.orc.vectorization_enabled)
            _put(result, "read.orc.batch-size", r.orc.batch_size)

    return result


def _put_operation(result: dict[str, str], prefix: str, op: object | None) -> None:
    if op is None:
        return
    _put(result, f"{prefix}.mode", getattr(op, "mode", None))
    _put(result, f"{prefix}.isolation-level", getattr(op, "isolation_level", None))
    _put(result, f"{prefix}.distribution-mode", getattr(op, "distribution_mode", None))


def _put_delete(result: dict[str, str], d: DeleteProperties | None) -> None:
    if d is None:
        return
    _put(result, "write.delete.mode", d.mode)
    _put(result, "write.delete.isolation-level", d.isolation_level)
    _put(result, "write.delete.distribution-mode", d.distribution_mode)
    _put(result, "write.delete.format.default", d.format_default)
    _put(result, "write.delete.target-file-size-bytes", d.target_file_size_bytes)
    _put_parquet(result, "write.delete.parquet", d.parquet)


def _put_parquet(result: dict[str, str], prefix: str, p: object | None) -> None:
    if p is None:
        return
    _put(result, f"{prefix}.compression-codec", getattr(p, "compression_codec", None))
    _put(result, f"{prefix}.compression-level", getattr(p, "compression_level", None))
    _put(result, f"{prefix}.row-group-size-bytes", getattr(p, "row_group_size_bytes", None))
    _put(result, f"{prefix}.page-size-bytes", getattr(p, "page_size_bytes", None))
    _put(result, f"{prefix}.dict-size-bytes", getattr(p, "dict_size_bytes", None))


def _put(result: dict[str, str], key: str, value: object | None) -> None:
    if value is not None:
        result[key] = str(value)


def _put_bool(result: dict[str, str], key: str, value: bool | None) -> None:
    if value is not None:
        result[key] = "true" if value else "false"
```

Now update `application/service/catalog/get_table.py`:

```python
"""Define the GetTableService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.get_table.input import GetTableInput
from application.port.inbound.catalog.get_table.output import (
    GetTableOutput,
    GetTableSchemaFieldOutput,
    GetTableSchemaOutput,
)
from application.port.inbound.catalog.get_table.use_case import GetTableUseCase
from application.service.catalog.table_properties_serializer import table_properties_to_dict

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog.gateway import (
        ReadCatalogGateway,
    )


class GetTableService(GetTableUseCase):
    """Get table metadata by delegating to ReadCatalogGateway."""

    def __init__(self, reader: ReadCatalogGateway) -> None:
        """Initialize with the catalog reader port."""
        self._reader = reader

    def execute(self, request: GetTableInput) -> GetTableOutput:
        """Load table and return metadata as output DTO."""
        table = self._reader.load_table(request.namespace, request.table)
        return GetTableOutput(
            name=table.name,
            namespace=table.namespace,
            location=table.location,
            current_snapshot_id=table.current_snapshot_id,
            schema=GetTableSchemaOutput(
                fields=[
                    GetTableSchemaFieldOutput(
                        field_id=f.field_id,
                        name=f.name,
                        field_type=f.field_type,
                        required=f.required,
                    )
                    for f in table.schema.fields
                ],
            ),
            properties=table_properties_to_dict(table.properties),
        )
```

- [ ] **Step 5: Update test_table.py — use TableProperties instead of dict**

Replace `"properties": {"write.format.default": "parquet"}` in `tests/application/domain/model/catalog/test_table.py`:

```python
"""Test the Table aggregate root."""

from __future__ import annotations

from base import AggregateRoot
from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.schema_field import SchemaField
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.snapshot_summary import SnapshotSummary
from application.domain.model.catalog.table import Table
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_properties.table_properties import TableProperties
from application.domain.model.catalog.table_properties.write_properties import WriteProperties
from application.domain.model.catalog.table_properties.format_properties import FormatProperties
from application.domain.model.catalog.table_schema import TableSchema


def _make_table(**overrides) -> Table:
    """Build a Table with sensible defaults, overridable per test."""
    defaults = {
        "id": TableId(value="default.orders"),
        "namespace": "default",
        "name": "orders",
        "location": "s3://warehouse/default/orders",
        "current_snapshot_id": 100,
        "schema": TableSchema(
            fields=(
                SchemaField(field_id=1, name="id", field_type="long", required=True),
            )
        ),
        "snapshots": (
            Snapshot(
                snapshot_id=100,
                parent_id=None,
                timestamp_ms=0,
                summary=SnapshotSummary(data={}),
            ),
        ),
        "branches": (Branch(id=BranchId(value="main"), snapshot_id=100),),
        "tags": (),
        "properties": TableProperties(
            write=WriteProperties(format=FormatProperties(default="parquet")),
        ),
    }
    defaults.update(overrides)
    return Table(**defaults)


def test_table_is_aggregate_root():
    """Table extends AggregateRoot."""
    assert issubclass(Table, AggregateRoot)


def test_table_fields():
    """Table stores all fields correctly."""
    t = _make_table()
    assert t.namespace == "default"
    assert t.name == "orders"
    assert t.location == "s3://warehouse/default/orders"
    assert t.current_snapshot_id == 100
    assert len(t.schema.fields) == 1
    assert len(t.snapshots) == 1
    assert len(t.branches) == 1
    assert len(t.tags) == 0


def test_table_equality_by_id():
    """Same TableId = equal, regardless of other fields."""
    a = _make_table(name="orders")
    b = _make_table(name="different")
    assert a == b


def test_table_inequality_by_id():
    """Different TableId = not equal."""
    a = _make_table(id=TableId(value="a.b"))
    b = _make_table(id=TableId(value="c.d"))
    assert a != b


def test_table_snapshots_are_tuple():
    """Snapshots collection is a tuple."""
    t = _make_table()
    assert isinstance(t.snapshots, tuple)


def test_table_branches_are_tuple():
    """Branches collection is a tuple."""
    t = _make_table()
    assert isinstance(t.branches, tuple)


def test_table_tags_are_tuple():
    """Tags collection is a tuple."""
    t = _make_table()
    assert isinstance(t.tags, tuple)


def test_table_properties_is_typed():
    """Properties is a TableProperties value object."""
    t = _make_table()
    assert isinstance(t.properties, TableProperties)
```

- [ ] **Step 6: Update test_get_table.py — use TableProperties**

```python
"""Test the GetTableService."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.schema_field import SchemaField
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.snapshot_summary import SnapshotSummary
from application.domain.model.catalog.table import Table
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_properties.table_properties import TableProperties
from application.domain.model.catalog.table_properties.write_properties import WriteProperties
from application.domain.model.catalog.table_properties.format_properties import FormatProperties
from application.domain.model.catalog.table_schema import TableSchema
from application.service.catalog.get_table import GetTableService
from application.port.inbound.catalog.get_table import (
    GetTableInput,
    GetTableOutput,
    GetTableUseCase,
)


def _make_table() -> Table:
    """Build a Table domain object for testing."""
    return Table(
        id=TableId(value="default.orders"),
        namespace="default",
        name="orders",
        location="s3://warehouse/default/orders",
        current_snapshot_id=100,
        schema=TableSchema(
            fields=(
                SchemaField(
                    field_id=1, name="order_id", field_type="long", required=True
                ),
                SchemaField(
                    field_id=2, name="amount", field_type="double", required=False
                ),
            ),
        ),
        snapshots=(
            Snapshot(
                snapshot_id=100,
                parent_id=None,
                timestamp_ms=0,
                summary=SnapshotSummary(data={}),
            ),
        ),
        branches=(Branch(id=BranchId(value="main"), snapshot_id=100),),
        tags=(),
        properties=TableProperties(
            write=WriteProperties(format=FormatProperties(default="parquet")),
        ),
    )


def test_implements_use_case():
    """GetTableService implements GetTableUseCase."""
    assert issubclass(GetTableService, GetTableUseCase)


def test_returns_table_metadata():
    """Service loads table and returns metadata output."""
    reader = MagicMock()
    reader.load_table.return_value = _make_table()
    service = GetTableService(reader)

    result = service.execute(GetTableInput(namespace="default", table="orders"))

    assert isinstance(result, GetTableOutput)
    assert result.name == "orders"
    assert result.namespace == "default"
    assert result.location == "s3://warehouse/default/orders"
    assert result.current_snapshot_id == 100
    assert len(result.schema.fields) == 2
    assert result.schema.fields[0].name == "order_id"
    assert result.properties == {"write.format.default": "parquet"}
    reader.load_table.assert_called_once_with("default", "orders")
```

- [ ] **Step 7: Update test_read_catalog_iceberg_gateway.py**

In `tests/adapter/outbound/catalog/test_read_catalog_iceberg_gateway.py`, update `test_load_table` assertion. Change line 121:

```python
    assert result.properties.write.format.default == "parquet"
```

Replace line 67:

```python
    mock_table.metadata.properties = {"write.format.default": "parquet"}
```

This stays the same (it's the mock PyIceberg response). Only the assertion changes.

- [ ] **Step 8: Run all tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS.

- [ ] **Step 9: Run lint-imports**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

Expected: PASS. The `table_properties_serializer.py` is in `application.service` which can import from `application.domain.model` — this is allowed.

- [ ] **Step 10: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(catalog): replace Table.properties dict with typed TableProperties"
```

---

## Task 8: UpdateTableProperties outbound port

**Files:**
- Create: `application/port/outbound/catalog/update_table_properties/__init__.py`
- Create: `application/port/outbound/catalog/update_table_properties/gateway.py`
- Create: `application/port/outbound/catalog/update_table_properties/input.py`
- Modify: `application/port/outbound/catalog/__init__.py`
- Modify: `application/port/outbound/__init__.py`

- [ ] **Step 1: Run existing architecture tests as baseline**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/architecture/ -v`

Expected: All PASS.

- [ ] **Step 2: Create the outbound port files**

Create `application/port/outbound/catalog/update_table_properties/gateway.py`:

```python
"""Define the UpdateTablePropertiesGateway port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.catalog.update_table_properties.input import (
        UpdateTablePropertiesInput,
    )


class UpdateTablePropertiesGateway(Gateway):
    """Gateway for updating Iceberg table properties via the catalog."""

    @abstractmethod
    def execute(self, input: UpdateTablePropertiesInput) -> None:
        """Set and/or remove table properties."""
        ...
```

Create `application/port/outbound/catalog/update_table_properties/input.py`:

```python
"""Define the UpdateTablePropertiesInput value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class UpdateTablePropertiesInput(ValueObject):
    """Primitive-only input for updating table properties via the catalog.

    Uses only primitive types so adapter implementations need zero domain imports.
    """

    namespace: str
    table: str
    updates: dict[str, str]
    removals: list[str]
```

Create `application/port/outbound/catalog/update_table_properties/__init__.py`:

```python
"""UpdateTableProperties gateway port."""

from application.port.outbound.catalog.update_table_properties.gateway import UpdateTablePropertiesGateway
from application.port.outbound.catalog.update_table_properties.input import UpdateTablePropertiesInput

__all__ = ["UpdateTablePropertiesGateway", "UpdateTablePropertiesInput"]
```

- [ ] **Step 3: Update __init__.py re-exports**

Update `application/port/outbound/catalog/__init__.py`:

```python
"""Catalog gateway port."""

from application.port.outbound.catalog.read_catalog import ReadCatalogGateway
from application.port.outbound.catalog.update_table_properties import (
    UpdateTablePropertiesGateway,
    UpdateTablePropertiesInput,
)

__all__ = [
    "ReadCatalogGateway",
    "UpdateTablePropertiesGateway",
    "UpdateTablePropertiesInput",
]
```

Update `application/port/outbound/__init__.py`:

```python
"""Outbound port interfaces (repositories, stores, gateways)."""

from application.port.outbound.catalog import (
    ReadCatalogGateway,
    UpdateTablePropertiesGateway,
    UpdateTablePropertiesInput as OutboundUpdateTablePropertiesInput,
)
from application.port.outbound.job import JobsRepo
from application.port.outbound.job_run import (
    SubmitJobRunGateway,
    JobRunsRepo,
    SubmitJobRunInput,
)

__all__ = [
    "ReadCatalogGateway",
    "UpdateTablePropertiesGateway",
    "OutboundUpdateTablePropertiesInput",
    "JobRunsRepo",
    "JobsRepo",
    "SubmitJobRunGateway",
    "SubmitJobRunInput",
]
```

- [ ] **Step 4: Run architecture tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/architecture/ -v`

Expected: All PASS — the new gateway follows the naming convention and structure rules.

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/application/port/outbound/catalog/
git commit -m "feat(catalog): add UpdateTablePropertiesGateway outbound port"
```

---

## Task 9: UpdateTableProperties inbound port + service

**Files:**
- Create: `application/port/inbound/catalog/update_table_properties/__init__.py`
- Create: `application/port/inbound/catalog/update_table_properties/input.py`
- Create: `application/port/inbound/catalog/update_table_properties/output.py`
- Create: `application/port/inbound/catalog/update_table_properties/use_case.py`
- Create: `application/service/catalog/update_table_properties.py`
- Modify: `application/port/inbound/catalog/__init__.py`
- Test: `tests/application/service/catalog/test_update_table_properties.py`

- [ ] **Step 1: Write the failing test**

Create `tests/application/service/catalog/test_update_table_properties.py`:

```python
"""Test the UpdateTablePropertiesService."""

from __future__ import annotations

from unittest.mock import MagicMock

from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.branch_id import BranchId
from application.domain.model.catalog.schema_field import SchemaField
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.snapshot_summary import SnapshotSummary
from application.domain.model.catalog.table import Table
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_properties.table_properties import TableProperties
from application.domain.model.catalog.table_properties.write_properties import WriteProperties
from application.domain.model.catalog.table_properties.format_properties import FormatProperties
from application.domain.model.catalog.table_properties.operation_properties import OperationProperties
from application.domain.model.catalog.table_properties.write_mode import WriteMode
from application.domain.model.catalog.table_schema import TableSchema
from application.port.inbound.catalog.update_table_properties import (
    UpdateTablePropertiesInput,
    UpdateTablePropertiesOutput,
    UpdateTablePropertiesUseCase,
)
from application.service.catalog.update_table_properties import UpdateTablePropertiesService


def _make_updated_table() -> Table:
    """Build a Table that represents the state after property update."""
    return Table(
        id=TableId(value="default.orders"),
        namespace="default",
        name="orders",
        location="s3://warehouse/default/orders",
        current_snapshot_id=100,
        schema=TableSchema(
            fields=(
                SchemaField(field_id=1, name="id", field_type="long", required=True),
            ),
        ),
        snapshots=(
            Snapshot(
                snapshot_id=100,
                parent_id=None,
                timestamp_ms=0,
                summary=SnapshotSummary(data={}),
            ),
        ),
        branches=(Branch(id=BranchId(value="main"), snapshot_id=100),),
        tags=(),
        properties=TableProperties(
            write=WriteProperties(
                merge=OperationProperties(mode=WriteMode.MERGE_ON_READ),
                format=FormatProperties(default="parquet"),
            ),
        ),
    )


def test_implements_use_case():
    """UpdateTablePropertiesService implements UpdateTablePropertiesUseCase."""
    assert issubclass(UpdateTablePropertiesService, UpdateTablePropertiesUseCase)


def test_splits_updates_and_removals():
    """Service splits input into updates (non-None) and removals (None)."""
    writer = MagicMock()
    reader = MagicMock()
    reader.load_table.return_value = _make_updated_table()
    service = UpdateTablePropertiesService(writer=writer, reader=reader)

    result = service.execute(
        UpdateTablePropertiesInput(
            namespace="default",
            table="orders",
            properties={
                "write.merge.mode": "merge-on-read",
                "write.delete.mode": None,
            },
        )
    )

    writer.execute.assert_called_once()
    call_input = writer.execute.call_args[0][0]
    assert call_input.namespace == "default"
    assert call_input.table == "orders"
    assert call_input.updates == {"write.merge.mode": "merge-on-read"}
    assert call_input.removals == ["write.delete.mode"]


def test_returns_updated_properties():
    """Service returns properties dict after update."""
    writer = MagicMock()
    reader = MagicMock()
    reader.load_table.return_value = _make_updated_table()
    service = UpdateTablePropertiesService(writer=writer, reader=reader)

    result = service.execute(
        UpdateTablePropertiesInput(
            namespace="default",
            table="orders",
            properties={"write.merge.mode": "merge-on-read"},
        )
    )

    assert isinstance(result, UpdateTablePropertiesOutput)
    assert result.properties["write.merge.mode"] == "merge-on-read"
    assert result.properties["write.format.default"] == "parquet"
    reader.load_table.assert_called_once_with("default", "orders")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/catalog/test_update_table_properties.py -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create inbound port files**

Create `application/port/inbound/catalog/update_table_properties/input.py`:

```python
"""Define the UpdateTablePropertiesInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateTablePropertiesInput:
    """Input for the UpdateTableProperties use case.

    properties: dict mapping Iceberg property keys to new values.
    A value of None means the property should be removed.
    """

    namespace: str
    table: str
    properties: dict[str, str | None]
```

Create `application/port/inbound/catalog/update_table_properties/output.py`:

```python
"""Define the UpdateTablePropertiesOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateTablePropertiesOutput:
    """Output for the UpdateTableProperties use case."""

    properties: dict[str, str]
```

Create `application/port/inbound/catalog/update_table_properties/use_case.py`:

```python
"""Define the UpdateTablePropertiesUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.catalog.update_table_properties.input import UpdateTablePropertiesInput
from application.port.inbound.catalog.update_table_properties.output import UpdateTablePropertiesOutput


class UpdateTablePropertiesUseCase(UseCase[UpdateTablePropertiesInput, UpdateTablePropertiesOutput]):
    """Update properties for a specific table."""
```

Create `application/port/inbound/catalog/update_table_properties/__init__.py`:

```python
"""UpdateTableProperties use case definition."""

from application.port.inbound.catalog.update_table_properties.input import UpdateTablePropertiesInput
from application.port.inbound.catalog.update_table_properties.output import UpdateTablePropertiesOutput
from application.port.inbound.catalog.update_table_properties.use_case import UpdateTablePropertiesUseCase

__all__ = [
    "UpdateTablePropertiesInput",
    "UpdateTablePropertiesOutput",
    "UpdateTablePropertiesUseCase",
]
```

- [ ] **Step 4: Create the service**

Create `application/service/catalog/update_table_properties.py`:

```python
"""Define the UpdateTablePropertiesService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.port.inbound.catalog.update_table_properties.input import UpdateTablePropertiesInput
from application.port.inbound.catalog.update_table_properties.output import UpdateTablePropertiesOutput
from application.port.inbound.catalog.update_table_properties.use_case import UpdateTablePropertiesUseCase
from application.port.outbound.catalog.update_table_properties.input import (
    UpdateTablePropertiesInput as OutboundInput,
)
from application.service.catalog.table_properties_serializer import table_properties_to_dict

if TYPE_CHECKING:
    from application.port.outbound.catalog.read_catalog.gateway import ReadCatalogGateway
    from application.port.outbound.catalog.update_table_properties.gateway import (
        UpdateTablePropertiesGateway,
    )


class UpdateTablePropertiesService(UpdateTablePropertiesUseCase):
    """Update table properties by delegating to the catalog gateway."""

    def __init__(
        self,
        writer: UpdateTablePropertiesGateway,
        reader: ReadCatalogGateway,
    ) -> None:
        """Initialize with writer and reader gateways."""
        self._writer = writer
        self._reader = reader

    def execute(self, request: UpdateTablePropertiesInput) -> UpdateTablePropertiesOutput:
        """Split properties into updates/removals, apply, and return updated state."""
        updates: dict[str, str] = {}
        removals: list[str] = []

        for key, value in request.properties.items():
            if value is None:
                removals.append(key)
            else:
                updates[key] = value

        self._writer.execute(
            OutboundInput(
                namespace=request.namespace,
                table=request.table,
                updates=updates,
                removals=removals,
            )
        )

        table = self._reader.load_table(request.namespace, request.table)
        return UpdateTablePropertiesOutput(
            properties=table_properties_to_dict(table.properties),
        )
```

- [ ] **Step 5: Update inbound catalog __init__.py**

Update `application/port/inbound/catalog/__init__.py` to add the new use case exports:

```python
"""Catalog use case definitions."""

from application.port.inbound.catalog.get_table import (
    GetTableInput,
    GetTableOutput,
    GetTableUseCase,
)
from application.port.inbound.catalog.list_branches import (
    ListBranchesInput,
    ListBranchesOutput,
    ListBranchesUseCase,
)
from application.port.inbound.catalog.list_namespaces import (
    ListNamespacesInput,
    ListNamespacesOutput,
    ListNamespacesUseCase,
)
from application.port.inbound.catalog.list_snapshots import (
    ListSnapshotsInput,
    ListSnapshotsOutput,
    ListSnapshotsUseCase,
)
from application.port.inbound.catalog.list_tables import (
    ListTablesInput,
    ListTablesOutput,
    ListTablesUseCase,
)
from application.port.inbound.catalog.list_tags import (
    ListTagsInput,
    ListTagsOutput,
    ListTagsUseCase,
)
from application.port.inbound.catalog.update_table_properties import (
    UpdateTablePropertiesInput,
    UpdateTablePropertiesOutput,
    UpdateTablePropertiesUseCase,
)

__all__ = [
    "GetTableInput",
    "GetTableOutput",
    "GetTableUseCase",
    "ListBranchesInput",
    "ListBranchesOutput",
    "ListBranchesUseCase",
    "ListNamespacesInput",
    "ListNamespacesOutput",
    "ListNamespacesUseCase",
    "ListSnapshotsInput",
    "ListSnapshotsOutput",
    "ListSnapshotsUseCase",
    "ListTablesInput",
    "ListTablesOutput",
    "ListTablesUseCase",
    "ListTagsInput",
    "ListTagsOutput",
    "ListTagsUseCase",
    "UpdateTablePropertiesInput",
    "UpdateTablePropertiesOutput",
    "UpdateTablePropertiesUseCase",
]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/catalog/test_update_table_properties.py -v`

Expected: All tests PASS.

- [ ] **Step 7: Run full test suite + lint-imports**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

Expected: All PASS.

- [ ] **Step 8: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "feat(catalog): add UpdateTableProperties use case and service"
```

---

## Task 10: Update CLAUDE.md + remove adapter duplicate + final verification

**Files:**
- Modify: `CLAUDE.md`
- Remove: `adapter/outbound/catalog/table_properties_to_dict.py` (if created in Task 6, it's now superseded by the service-layer version)

- [ ] **Step 1: Update CLAUDE.md gateway verb vocabulary**

In `CLAUDE.md`, find the line:

```
**Gateway verb vocabulary** (new verbs require review): `Read`, `Submit`, `Send`, `Publish`, `Poll`, `Sync`, `Write`, `Delete`.
```

Replace with:

```
**Gateway verb vocabulary** (new verbs require review): `Read`, `Submit`, `Send`, `Publish`, `Poll`, `Sync`, `Write`, `Delete`, `Update`.
```

- [ ] **Step 2: Remove adapter-layer table_properties_to_dict if it exists**

If `adapter/outbound/catalog/table_properties_to_dict.py` was created in Task 6, delete it — the canonical version now lives in `application/service/catalog/table_properties_serializer.py`. Also update `adapter/outbound/catalog/dict_to_table_properties.py` tests if they import from the adapter version.

Check `tests/adapter/outbound/catalog/test_table_properties_to_dict.py` — update the import path to use the service-layer version:

```python
from application.service.catalog.table_properties_serializer import table_properties_to_dict
```

Or move the test to `tests/application/service/catalog/test_table_properties_serializer.py`.

- [ ] **Step 3: Run full verification**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: add Update to gateway verb vocabulary, clean up duplicate converter"
```
