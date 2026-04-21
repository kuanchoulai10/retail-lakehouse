# Catalog Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only REST API endpoints to browse Iceberg catalog metadata (namespaces, tables, snapshots, branches, tags) via PyIceberg.

**Architecture:** Simplified adapter-only architecture (no DDD domain/use-case layers). PyIceberg client wrapper in outbound adapter, FastAPI routes in inbound adapter, DI via FastAPI Depends. Each endpoint is one file, following existing project conventions.

**Tech Stack:** PyIceberg (REST catalog), FastAPI, Pydantic (response DTOs), pytest + httpx (testing)

**Spec:** `docs/superpowers/specs/2026-04-21-catalog-browser-design.md`

---

## File Map

### New Files

| File | Responsibility |
|------|---------------|
| `adapter/outbound/catalog/__init__.py` | Package init, re-exports `IcebergCatalogClient` |
| `adapter/outbound/catalog/iceberg_catalog_client.py` | Wraps PyIceberg catalog: list namespaces, tables, load table metadata, snapshots, refs |
| `adapter/inbound/web/catalog/__init__.py` | Catalog router, aggregates sub-routers |
| `adapter/inbound/web/catalog/dto.py` | Response DTOs: namespace, table, snapshot, branch, tag |
| `adapter/inbound/web/catalog/list_namespaces.py` | `GET /v1/catalogs/{catalog}/namespaces` |
| `adapter/inbound/web/catalog/list_tables.py` | `GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables` |
| `adapter/inbound/web/catalog/get_table.py` | `GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}` |
| `adapter/inbound/web/catalog/list_snapshots.py` | `GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots` |
| `adapter/inbound/web/catalog/list_branches.py` | `GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches` |
| `adapter/inbound/web/catalog/list_tags.py` | `GET /v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags` |
| `dependencies/catalog.py` | `get_catalog_client()` FastAPI dependency |
| `tests/configs/test_iceberg_settings.py` | Tests for new AppSettings iceberg fields |
| `tests/adapter/outbound/catalog/__init__.py` | Test package init |
| `tests/adapter/outbound/catalog/test_iceberg_catalog_client.py` | Tests for PyIceberg client wrapper |
| `tests/adapter/inbound/web/catalog/__init__.py` | Test package init |
| `tests/adapter/inbound/web/catalog/test_list_namespaces.py` | Route test |
| `tests/adapter/inbound/web/catalog/test_list_tables.py` | Route test |
| `tests/adapter/inbound/web/catalog/test_get_table.py` | Route test |
| `tests/adapter/inbound/web/catalog/test_list_snapshots.py` | Route test |
| `tests/adapter/inbound/web/catalog/test_list_branches.py` | Route test |
| `tests/adapter/inbound/web/catalog/test_list_tags.py` | Route test |

### Modified Files

| File | Change |
|------|--------|
| `configs/app.py` | Add `iceberg_catalog_uri` and `iceberg_catalog_name` fields |
| `pyproject.toml` | Add `pyiceberg` dependency |
| `adapter/inbound/web/__init__.py` | Include catalog router |
| `main.py` | No changes needed (router auto-included via `adapter/inbound/web/__init__.py`) |
| `.importlinter` | Add `adapter.outbound.catalog` to ignore lists for catalog DI |

All file paths below are relative to `src/table-maintenance/backend/`.

---

## Task 1: Add PyIceberg dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pyiceberg to dependencies**

In `pyproject.toml`, add `pyiceberg` to the `dependencies` list:

```toml
dependencies = [
    "fastapi[standard]>=0.115",
    "kubernetes>=32.0",
    "sqlalchemy>=2.0",
    "psycopg[binary]>=3.2",
    "pyiceberg>=0.9",
]
```

- [ ] **Step 2: Lock dependencies**

Run:
```bash
uv lock --project src/table-maintenance/backend
```

Expected: lockfile updated without errors.

- [ ] **Step 3: Verify import works**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend python -c "from pyiceberg.catalog import load_catalog; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add src/table-maintenance/backend/pyproject.toml uv.lock
git commit -m "feat(catalog): add pyiceberg dependency"
```

---

## Task 2: Add iceberg settings to AppSettings

**Files:**
- Modify: `configs/app.py`
- Create: `tests/configs/test_iceberg_settings.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/configs/test_iceberg_settings.py`:

```python
"""Tests for AppSettings Iceberg catalog configuration."""

from configs import AppSettings


def test_iceberg_catalog_uri_default():
    """Verify that iceberg_catalog_uri defaults to Polaris endpoint."""
    s = AppSettings()
    assert s.iceberg_catalog_uri == "http://polaris:8181/api/catalog"


def test_iceberg_catalog_name_default():
    """Verify that iceberg_catalog_name defaults to 'iceberg'."""
    s = AppSettings()
    assert s.iceberg_catalog_name == "iceberg"


def test_iceberg_catalog_uri_env_override(monkeypatch):
    """Verify that BACKEND_ICEBERG_CATALOG_URI overrides the default."""
    monkeypatch.setenv("BACKEND_ICEBERG_CATALOG_URI", "http://custom:9999/api/catalog")
    s = AppSettings()
    assert s.iceberg_catalog_uri == "http://custom:9999/api/catalog"


def test_iceberg_catalog_name_env_override(monkeypatch):
    """Verify that BACKEND_ICEBERG_CATALOG_NAME overrides the default."""
    monkeypatch.setenv("BACKEND_ICEBERG_CATALOG_NAME", "my_catalog")
    s = AppSettings()
    assert s.iceberg_catalog_name == "my_catalog"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/configs/test_iceberg_settings.py -v
```

Expected: FAIL — `AttributeError: 'AppSettings' object has no attribute 'iceberg_catalog_uri'`

- [ ] **Step 3: Add iceberg fields to AppSettings**

In `configs/app.py`, add two fields to the `AppSettings` class:

```python
iceberg_catalog_uri: str = "http://polaris:8181/api/catalog"
iceberg_catalog_name: str = "iceberg"
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/configs/test_iceberg_settings.py -v
```

Expected: 4 passed

- [ ] **Step 5: Run full test suite**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v
```

Expected: all tests pass (no regressions from new fields)

- [ ] **Step 6: Commit**

```bash
git add src/table-maintenance/backend/configs/app.py src/table-maintenance/backend/tests/configs/test_iceberg_settings.py
git commit -m "feat(catalog): add iceberg catalog settings to AppSettings"
```

---

## Task 3: Create PyIceberg catalog client wrapper

**Files:**
- Create: `adapter/outbound/catalog/__init__.py`
- Create: `adapter/outbound/catalog/iceberg_catalog_client.py`
- Create: `tests/adapter/outbound/catalog/__init__.py`
- Create: `tests/adapter/outbound/catalog/test_iceberg_catalog_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/adapter/outbound/catalog/__init__.py`:

```python
"""Tests for the Iceberg catalog outbound adapter."""
```

Create `tests/adapter/outbound/catalog/test_iceberg_catalog_client.py`:

```python
"""Tests for IcebergCatalogClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient


@pytest.fixture
def mock_pyiceberg_catalog():
    """Return a mock PyIceberg catalog."""
    return MagicMock()


@pytest.fixture
def client(mock_pyiceberg_catalog):
    """Return an IcebergCatalogClient wrapping a mock catalog."""
    with patch(
        "adapter.outbound.catalog.iceberg_catalog_client.load_catalog",
        return_value=mock_pyiceberg_catalog,
    ):
        return IcebergCatalogClient(
            catalog_uri="http://polaris:8181/api/catalog",
            catalog_name="iceberg",
        )


def test_list_namespaces(client, mock_pyiceberg_catalog):
    """Return namespace names as a list of strings."""
    mock_pyiceberg_catalog.list_namespaces.return_value = [
        ("default",),
        ("raw",),
    ]
    result = client.list_namespaces()
    assert result == ["default", "raw"]
    mock_pyiceberg_catalog.list_namespaces.assert_called_once()


def test_list_tables(client, mock_pyiceberg_catalog):
    """Return table names as a list of strings."""
    mock_pyiceberg_catalog.list_tables.return_value = [
        ("default", "orders"),
        ("default", "products"),
    ]
    result = client.list_tables("default")
    assert result == ["orders", "products"]
    mock_pyiceberg_catalog.list_tables.assert_called_once_with(namespace="default")


def test_get_table(client, mock_pyiceberg_catalog):
    """Return table metadata as a plain dict."""
    mock_table = MagicMock()
    mock_table.metadata.current_snapshot_id = 123
    mock_table.metadata.location = "s3://warehouse/default/orders"
    mock_table.metadata.properties = {"write.format.default": "parquet"}

    mock_field = MagicMock()
    mock_field.field_id = 1
    mock_field.name = "order_id"
    mock_field.field_type = MagicMock()
    mock_field.field_type.__str__ = lambda self: "long"
    mock_field.required = True
    mock_table.schema.return_value.fields = (mock_field,)

    mock_pyiceberg_catalog.load_table.return_value = mock_table
    result = client.get_table("default", "orders")

    assert result["table"] == "orders"
    assert result["namespace"] == "default"
    assert result["location"] == "s3://warehouse/default/orders"
    assert result["current_snapshot_id"] == 123
    assert result["schema"]["fields"][0]["name"] == "order_id"
    assert result["properties"] == {"write.format.default": "parquet"}


def test_list_snapshots(client, mock_pyiceberg_catalog):
    """Return snapshots as a list of dicts."""
    mock_snap = MagicMock()
    mock_snap.snapshot_id = 100
    mock_snap.parent_snapshot_id = None
    mock_snap.timestamp_ms = 1713600000000
    mock_snap.summary = {"operation": "append", "added-records": "50"}

    mock_table = MagicMock()
    mock_table.metadata.snapshots = [mock_snap]
    mock_pyiceberg_catalog.load_table.return_value = mock_table

    result = client.list_snapshots("default", "orders")
    assert len(result) == 1
    assert result[0]["snapshot_id"] == 100
    assert result[0]["parent_id"] is None
    assert result[0]["timestamp_ms"] == 1713600000000
    assert result[0]["summary"] == {"operation": "append", "added-records": "50"}


def test_list_branches(client, mock_pyiceberg_catalog):
    """Return only branch refs."""
    main_ref = MagicMock()
    main_ref.snapshot_id = 100
    main_ref.snapshot_ref_type = "branch"
    main_ref.max_ref_age_ms = None
    main_ref.max_snapshot_age_ms = None
    main_ref.min_snapshots_to_keep = None

    tag_ref = MagicMock()
    tag_ref.snapshot_ref_type = "tag"

    mock_table = MagicMock()
    mock_table.metadata.refs = {"main": main_ref, "v1.0": tag_ref}
    mock_pyiceberg_catalog.load_table.return_value = mock_table

    result = client.list_branches("default", "orders")
    assert len(result) == 1
    assert result[0]["name"] == "main"
    assert result[0]["snapshot_id"] == 100


def test_list_tags(client, mock_pyiceberg_catalog):
    """Return only tag refs."""
    branch_ref = MagicMock()
    branch_ref.snapshot_ref_type = "branch"

    tag_ref = MagicMock()
    tag_ref.snapshot_id = 200
    tag_ref.snapshot_ref_type = "tag"
    tag_ref.max_ref_age_ms = None

    mock_table = MagicMock()
    mock_table.metadata.refs = {"main": branch_ref, "v1.0": tag_ref}
    mock_pyiceberg_catalog.load_table.return_value = mock_table

    result = client.list_tags("default", "orders")
    assert len(result) == 1
    assert result[0]["name"] == "v1.0"
    assert result[0]["snapshot_id"] == 200


def test_list_namespaces_not_found(client, mock_pyiceberg_catalog):
    """Raise ValueError when catalog returns an error."""
    from pyiceberg.exceptions import NoSuchNamespaceError

    mock_pyiceberg_catalog.list_namespaces.side_effect = NoSuchNamespaceError("nope")
    with pytest.raises(NoSuchNamespaceError):
        client.list_namespaces()


def test_get_table_not_found(client, mock_pyiceberg_catalog):
    """Raise NoSuchTableError when table does not exist."""
    from pyiceberg.exceptions import NoSuchTableError

    mock_pyiceberg_catalog.load_table.side_effect = NoSuchTableError("nope")
    with pytest.raises(NoSuchTableError):
        client.get_table("default", "nonexistent")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/catalog/ -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'adapter.outbound.catalog'`

- [ ] **Step 3: Write the IcebergCatalogClient**

Create `adapter/outbound/catalog/__init__.py`:

```python
"""Iceberg catalog outbound adapter."""

from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient

__all__ = ["IcebergCatalogClient"]
```

Create `adapter/outbound/catalog/iceberg_catalog_client.py`:

```python
"""PyIceberg-based catalog client for reading Iceberg metadata."""

from __future__ import annotations

from pyiceberg.catalog import load_catalog


class IcebergCatalogClient:
    """Wrap PyIceberg catalog operations, returning plain dicts."""

    def __init__(self, catalog_uri: str, catalog_name: str) -> None:
        self._catalog = load_catalog(
            name=catalog_name,
            type="rest",
            uri=catalog_uri,
        )

    def list_namespaces(self) -> list[str]:
        """Return namespace names as a flat list of strings."""
        raw = self._catalog.list_namespaces()
        return [ns[0] for ns in raw]

    def list_tables(self, namespace: str) -> list[str]:
        """Return table names within a namespace."""
        raw = self._catalog.list_tables(namespace=namespace)
        return [tbl[-1] for tbl in raw]

    def get_table(self, namespace: str, table: str) -> dict:
        """Return table metadata as a plain dict."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        schema_fields = [
            {
                "id": f.field_id,
                "name": f.name,
                "type": str(f.field_type),
                "required": f.required,
            }
            for f in tbl.schema().fields
        ]
        return {
            "table": table,
            "namespace": namespace,
            "location": tbl.metadata.location,
            "current_snapshot_id": tbl.metadata.current_snapshot_id,
            "schema": {"fields": schema_fields},
            "properties": dict(tbl.metadata.properties),
        }

    def list_snapshots(self, namespace: str, table: str) -> list[dict]:
        """Return snapshots as a list of plain dicts."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        return [
            {
                "snapshot_id": snap.snapshot_id,
                "parent_id": snap.parent_snapshot_id,
                "timestamp_ms": snap.timestamp_ms,
                "summary": dict(snap.summary),
            }
            for snap in tbl.metadata.snapshots
        ]

    def list_branches(self, namespace: str, table: str) -> list[dict]:
        """Return branch refs as a list of plain dicts."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        return [
            {
                "name": name,
                "snapshot_id": ref.snapshot_id,
                "max_snapshot_age_ms": ref.max_snapshot_age_ms,
                "max_ref_age_ms": ref.max_ref_age_ms,
                "min_snapshots_to_keep": ref.min_snapshots_to_keep,
            }
            for name, ref in tbl.metadata.refs.items()
            if ref.snapshot_ref_type == "branch"
        ]

    def list_tags(self, namespace: str, table: str) -> list[dict]:
        """Return tag refs as a list of plain dicts."""
        tbl = self._catalog.load_table(f"{namespace}.{table}")
        return [
            {
                "name": name,
                "snapshot_id": ref.snapshot_id,
                "max_ref_age_ms": ref.max_ref_age_ms,
            }
            for name, ref in tbl.metadata.refs.items()
            if ref.snapshot_ref_type == "tag"
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/catalog/ -v
```

Expected: 8 passed

- [ ] **Step 5: Run full test suite**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/table-maintenance/backend/adapter/outbound/catalog/ src/table-maintenance/backend/tests/adapter/outbound/catalog/
git commit -m "feat(catalog): add PyIceberg catalog client wrapper"
```

---

## Task 4: Add catalog dependency and response DTOs

**Files:**
- Create: `dependencies/catalog.py`
- Create: `adapter/inbound/web/catalog/__init__.py`
- Create: `adapter/inbound/web/catalog/dto.py`
- Modify: `.importlinter` (add catalog DI ignore)

- [ ] **Step 1: Create the catalog dependency**

Create `dependencies/catalog.py`:

```python
"""Provide the Iceberg catalog client dependency."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from configs import AppSettings
from dependencies.settings import get_settings


@lru_cache(maxsize=1)
def _catalog_client_singleton(uri: str, name: str) -> IcebergCatalogClient:
    return IcebergCatalogClient(catalog_uri=uri, catalog_name=name)


def get_catalog_client(
    settings: AppSettings = Depends(get_settings),
) -> IcebergCatalogClient:
    """Return a cached IcebergCatalogClient based on AppSettings."""
    return _catalog_client_singleton(
        uri=settings.iceberg_catalog_uri,
        name=settings.iceberg_catalog_name,
    )
```

- [ ] **Step 2: Create the response DTOs**

Create `adapter/inbound/web/catalog/dto.py`:

```python
"""Catalog API response DTOs."""

from __future__ import annotations

from pydantic import BaseModel


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
    schema_: SchemaResponse
    properties: dict[str, str]

    class Config:
        """Use schema_ to avoid Pydantic reserved name conflict."""

        populate_by_name = True

    model_config = {"json_schema_extra": {"properties": {"schema": {"$ref": "#/$defs/SchemaResponse"}}}}


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
```

- [ ] **Step 3: Create the catalog router package init**

Create `adapter/inbound/web/catalog/__init__.py`:

```python
"""Catalog REST API endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["catalog"])
```

This is a placeholder — routes will be added in Tasks 5–10.

- [ ] **Step 4: Update import-linter config**

In `.importlinter`, add catalog DI ignore to the `inbound-adapter-no-domain` contract's `ignore_imports`:

```
    dependencies.catalog -> adapter.outbound.catalog.iceberg_catalog_client
```

And add to the `inbound-outbound-separation` contract's `ignore_imports`:

```
    dependencies.catalog -> adapter.outbound.catalog.iceberg_catalog_client
```

- [ ] **Step 5: Register catalog router in web adapter**

Modify `adapter/inbound/web/__init__.py`:

```python
"""FastAPI web adapter."""

from fastapi import APIRouter

from adapter.inbound.web.catalog import router as catalog_router
from adapter.inbound.web.job import router as job_router
from adapter.inbound.web.job_run import router as job_run_router

router = APIRouter(prefix="/v1")
router.include_router(job_router)
router.include_router(job_run_router)
router.include_router(catalog_router)
```

- [ ] **Step 6: Run lint-imports to verify architecture rules pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports
```

Expected: all contracts pass

- [ ] **Step 7: Run full test suite**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v
```

Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add src/table-maintenance/backend/dependencies/catalog.py src/table-maintenance/backend/adapter/inbound/web/catalog/ src/table-maintenance/backend/adapter/inbound/web/__init__.py src/table-maintenance/backend/.importlinter
git commit -m "feat(catalog): add catalog DI, DTOs, and router scaffold"
```

---

## Task 5: GET /namespaces endpoint

**Files:**
- Create: `adapter/inbound/web/catalog/list_namespaces.py`
- Create: `tests/adapter/inbound/web/catalog/__init__.py`
- Create: `tests/adapter/inbound/web/catalog/test_list_namespaces.py`
- Modify: `adapter/inbound/web/catalog/__init__.py` (register route)

- [ ] **Step 1: Write the failing test**

Create `tests/adapter/inbound/web/catalog/__init__.py`:

```python
"""Tests for the catalog web adapter."""
```

Create `tests/adapter/inbound/web/catalog/test_list_namespaces.py`:

```python
"""Tests for list namespaces endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.catalog import get_catalog_client
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router


def _make_client(mock_catalog_client: MagicMock) -> TestClient:
    """Provide a test client with the catalog client overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_catalog_client] = lambda: mock_catalog_client
    return TestClient(app)


def test_list_namespaces_returns_200():
    """Return 200 with a list of namespace names."""
    mock = MagicMock()
    mock.list_namespaces.return_value = ["default", "raw"]
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces")

    assert response.status_code == 200
    assert response.json() == {"namespaces": ["default", "raw"]}


def test_list_namespaces_empty():
    """Return 200 with an empty list when no namespaces exist."""
    mock = MagicMock()
    mock.list_namespaces.return_value = []
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces")

    assert response.status_code == 200
    assert response.json() == {"namespaces": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_namespaces.py -v
```

Expected: FAIL — 404 (route not registered yet)

- [ ] **Step 3: Create the route**

Create `adapter/inbound/web/catalog/list_namespaces.py`:

```python
"""Define the GET /catalogs/{catalog}/namespaces endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import NamespacesResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces",
    response_model=NamespacesResponse,
)
def list_namespaces(
    catalog: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> NamespacesResponse:
    """Return all namespaces in the catalog."""
    namespaces = client.list_namespaces()
    return NamespacesResponse(namespaces=namespaces)
```

- [ ] **Step 4: Register route in catalog router**

Update `adapter/inbound/web/catalog/__init__.py`:

```python
"""Catalog REST API endpoints."""

from fastapi import APIRouter

from adapter.inbound.web.catalog.list_namespaces import router as list_namespaces_router

router = APIRouter(tags=["catalog"])
router.include_router(list_namespaces_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_namespaces.py -v
```

Expected: 2 passed

- [ ] **Step 6: Run full test suite + lint-imports**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports
```

Expected: all tests pass, all contracts pass

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/adapter/inbound/web/catalog/ src/table-maintenance/backend/tests/adapter/inbound/web/catalog/
git commit -m "feat(catalog): add GET /namespaces endpoint"
```

---

## Task 6: GET /tables endpoint

**Files:**
- Create: `adapter/inbound/web/catalog/list_tables.py`
- Create: `tests/adapter/inbound/web/catalog/test_list_tables.py`
- Modify: `adapter/inbound/web/catalog/__init__.py` (register route)

- [ ] **Step 1: Write the failing test**

Create `tests/adapter/inbound/web/catalog/test_list_tables.py`:

```python
"""Tests for list tables endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.catalog import get_catalog_client
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router


def _make_client(mock_catalog_client: MagicMock) -> TestClient:
    """Provide a test client with the catalog client overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_catalog_client] = lambda: mock_catalog_client
    return TestClient(app)


def test_list_tables_returns_200():
    """Return 200 with a list of table names."""
    mock = MagicMock()
    mock.list_tables.return_value = ["orders", "products"]
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables")

    assert response.status_code == 200
    assert response.json() == {"tables": ["orders", "products"]}
    mock.list_tables.assert_called_once_with("default")


def test_list_tables_empty():
    """Return 200 with an empty list when no tables exist."""
    mock = MagicMock()
    mock.list_tables.return_value = []
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables")

    assert response.status_code == 200
    assert response.json() == {"tables": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_tables.py -v
```

Expected: FAIL — 404

- [ ] **Step 3: Create the route**

Create `adapter/inbound/web/catalog/list_tables.py`:

```python
"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import TablesResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables",
    response_model=TablesResponse,
)
def list_tables(
    catalog: str,
    namespace: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> TablesResponse:
    """Return all tables in the namespace."""
    tables = client.list_tables(namespace)
    return TablesResponse(tables=tables)
```

- [ ] **Step 4: Register route in catalog router**

Update `adapter/inbound/web/catalog/__init__.py` to add:

```python
from adapter.inbound.web.catalog.list_tables import router as list_tables_router

router.include_router(list_tables_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_tables.py -v
```

Expected: 2 passed

- [ ] **Step 6: Run full test suite + lint-imports**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/adapter/inbound/web/catalog/ src/table-maintenance/backend/tests/adapter/inbound/web/catalog/test_list_tables.py
git commit -m "feat(catalog): add GET /tables endpoint"
```

---

## Task 7: GET /table metadata endpoint

**Files:**
- Create: `adapter/inbound/web/catalog/get_table.py`
- Create: `tests/adapter/inbound/web/catalog/test_get_table.py`
- Modify: `adapter/inbound/web/catalog/__init__.py` (register route)

- [ ] **Step 1: Write the failing test**

Create `tests/adapter/inbound/web/catalog/test_get_table.py`:

```python
"""Tests for get table metadata endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.catalog import get_catalog_client
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router


def _make_client(mock_catalog_client: MagicMock) -> TestClient:
    """Provide a test client with the catalog client overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_catalog_client] = lambda: mock_catalog_client
    return TestClient(app)


SAMPLE_TABLE = {
    "table": "orders",
    "namespace": "default",
    "location": "s3://warehouse/default/orders",
    "current_snapshot_id": 123,
    "schema": {
        "fields": [
            {"id": 1, "name": "order_id", "type": "long", "required": True},
        ],
    },
    "properties": {"write.format.default": "parquet"},
}


def test_get_table_returns_200():
    """Return 200 with table metadata."""
    mock = MagicMock()
    mock.get_table.return_value = SAMPLE_TABLE
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders")

    assert response.status_code == 200
    body = response.json()
    assert body["table"] == "orders"
    assert body["namespace"] == "default"
    assert body["location"] == "s3://warehouse/default/orders"
    assert body["current_snapshot_id"] == 123
    assert len(body["schema"]["fields"]) == 1
    assert body["schema"]["fields"][0]["name"] == "order_id"
    mock.get_table.assert_called_once_with("default", "orders")
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_get_table.py -v
```

Expected: FAIL — 404

- [ ] **Step 3: Create the route**

Create `adapter/inbound/web/catalog/get_table.py`:

```python
"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table} endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import TableDetailResponse, SchemaResponse, SchemaFieldResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}",
    response_model=TableDetailResponse,
)
def get_table(
    catalog: str,
    namespace: str,
    table: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> TableDetailResponse:
    """Return metadata for a specific table."""
    data = client.get_table(namespace, table)
    return TableDetailResponse(
        table=data["table"],
        namespace=data["namespace"],
        location=data["location"],
        current_snapshot_id=data["current_snapshot_id"],
        schema_=SchemaResponse(
            fields=[SchemaFieldResponse(**f) for f in data["schema"]["fields"]],
        ),
        properties=data["properties"],
    )
```

- [ ] **Step 4: Register route in catalog router**

Update `adapter/inbound/web/catalog/__init__.py` to add:

```python
from adapter.inbound.web.catalog.get_table import router as get_table_router

router.include_router(get_table_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_get_table.py -v
```

Expected: 1 passed

- [ ] **Step 6: Run full test suite + lint-imports**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/adapter/inbound/web/catalog/ src/table-maintenance/backend/tests/adapter/inbound/web/catalog/test_get_table.py
git commit -m "feat(catalog): add GET /table metadata endpoint"
```

---

## Task 8: GET /snapshots endpoint

**Files:**
- Create: `adapter/inbound/web/catalog/list_snapshots.py`
- Create: `tests/adapter/inbound/web/catalog/test_list_snapshots.py`
- Modify: `adapter/inbound/web/catalog/__init__.py` (register route)

- [ ] **Step 1: Write the failing test**

Create `tests/adapter/inbound/web/catalog/test_list_snapshots.py`:

```python
"""Tests for list snapshots endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.catalog import get_catalog_client
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router


def _make_client(mock_catalog_client: MagicMock) -> TestClient:
    """Provide a test client with the catalog client overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_catalog_client] = lambda: mock_catalog_client
    return TestClient(app)


def test_list_snapshots_returns_200():
    """Return 200 with a list of snapshots."""
    mock = MagicMock()
    mock.list_snapshots.return_value = [
        {
            "snapshot_id": 100,
            "parent_id": None,
            "timestamp_ms": 1713600000000,
            "summary": {"operation": "append", "added-records": "50"},
        },
    ]
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/snapshots")

    assert response.status_code == 200
    body = response.json()
    assert len(body["snapshots"]) == 1
    assert body["snapshots"][0]["snapshot_id"] == 100
    assert body["snapshots"][0]["parent_id"] is None
    assert body["snapshots"][0]["summary"]["operation"] == "append"
    mock.list_snapshots.assert_called_once_with("default", "orders")


def test_list_snapshots_empty():
    """Return 200 with empty list when table has no snapshots."""
    mock = MagicMock()
    mock.list_snapshots.return_value = []
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/snapshots")

    assert response.status_code == 200
    assert response.json() == {"snapshots": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_snapshots.py -v
```

Expected: FAIL — 404

- [ ] **Step 3: Create the route**

Create `adapter/inbound/web/catalog/list_snapshots.py`:

```python
"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import SnapshotResponse, SnapshotsResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/snapshots",
    response_model=SnapshotsResponse,
)
def list_snapshots(
    catalog: str,
    namespace: str,
    table: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> SnapshotsResponse:
    """Return all snapshots for a table."""
    snapshots = client.list_snapshots(namespace, table)
    return SnapshotsResponse(
        snapshots=[SnapshotResponse(**s) for s in snapshots],
    )
```

- [ ] **Step 4: Register route in catalog router**

Update `adapter/inbound/web/catalog/__init__.py` to add:

```python
from adapter.inbound.web.catalog.list_snapshots import router as list_snapshots_router

router.include_router(list_snapshots_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_snapshots.py -v
```

Expected: 2 passed

- [ ] **Step 6: Run full test suite + lint-imports**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/adapter/inbound/web/catalog/ src/table-maintenance/backend/tests/adapter/inbound/web/catalog/test_list_snapshots.py
git commit -m "feat(catalog): add GET /snapshots endpoint"
```

---

## Task 9: GET /branches endpoint

**Files:**
- Create: `adapter/inbound/web/catalog/list_branches.py`
- Create: `tests/adapter/inbound/web/catalog/test_list_branches.py`
- Modify: `adapter/inbound/web/catalog/__init__.py` (register route)

- [ ] **Step 1: Write the failing test**

Create `tests/adapter/inbound/web/catalog/test_list_branches.py`:

```python
"""Tests for list branches endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.catalog import get_catalog_client
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router


def _make_client(mock_catalog_client: MagicMock) -> TestClient:
    """Provide a test client with the catalog client overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_catalog_client] = lambda: mock_catalog_client
    return TestClient(app)


def test_list_branches_returns_200():
    """Return 200 with a list of branch refs."""
    mock = MagicMock()
    mock.list_branches.return_value = [
        {
            "name": "main",
            "snapshot_id": 100,
            "max_snapshot_age_ms": None,
            "max_ref_age_ms": None,
            "min_snapshots_to_keep": None,
        },
    ]
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/branches")

    assert response.status_code == 200
    body = response.json()
    assert len(body["branches"]) == 1
    assert body["branches"][0]["name"] == "main"
    assert body["branches"][0]["snapshot_id"] == 100
    mock.list_branches.assert_called_once_with("default", "orders")


def test_list_branches_empty():
    """Return 200 with empty list when table has no branches."""
    mock = MagicMock()
    mock.list_branches.return_value = []
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/branches")

    assert response.status_code == 200
    assert response.json() == {"branches": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_branches.py -v
```

Expected: FAIL — 404

- [ ] **Step 3: Create the route**

Create `adapter/inbound/web/catalog/list_branches.py`:

```python
"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import BranchResponse, BranchesResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/branches",
    response_model=BranchesResponse,
)
def list_branches(
    catalog: str,
    namespace: str,
    table: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> BranchesResponse:
    """Return all branches for a table."""
    branches = client.list_branches(namespace, table)
    return BranchesResponse(
        branches=[BranchResponse(**b) for b in branches],
    )
```

- [ ] **Step 4: Register route in catalog router**

Update `adapter/inbound/web/catalog/__init__.py` to add:

```python
from adapter.inbound.web.catalog.list_branches import router as list_branches_router

router.include_router(list_branches_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_branches.py -v
```

Expected: 2 passed

- [ ] **Step 6: Run full test suite + lint-imports**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/adapter/inbound/web/catalog/ src/table-maintenance/backend/tests/adapter/inbound/web/catalog/test_list_branches.py
git commit -m "feat(catalog): add GET /branches endpoint"
```

---

## Task 10: GET /tags endpoint

**Files:**
- Create: `adapter/inbound/web/catalog/list_tags.py`
- Create: `tests/adapter/inbound/web/catalog/test_list_tags.py`
- Modify: `adapter/inbound/web/catalog/__init__.py` (register route)

- [ ] **Step 1: Write the failing test**

Create `tests/adapter/inbound/web/catalog/test_list_tags.py`:

```python
"""Tests for list tags endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.catalog import get_catalog_client
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adapter.inbound.web import router


def _make_client(mock_catalog_client: MagicMock) -> TestClient:
    """Provide a test client with the catalog client overridden."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_catalog_client] = lambda: mock_catalog_client
    return TestClient(app)


def test_list_tags_returns_200():
    """Return 200 with a list of tag refs."""
    mock = MagicMock()
    mock.list_tags.return_value = [
        {
            "name": "v1.0",
            "snapshot_id": 200,
            "max_ref_age_ms": None,
        },
    ]
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/tags")

    assert response.status_code == 200
    body = response.json()
    assert len(body["tags"]) == 1
    assert body["tags"][0]["name"] == "v1.0"
    assert body["tags"][0]["snapshot_id"] == 200
    mock.list_tags.assert_called_once_with("default", "orders")


def test_list_tags_empty():
    """Return 200 with empty list when table has no tags."""
    mock = MagicMock()
    mock.list_tags.return_value = []
    client = _make_client(mock)

    response = client.get("/v1/catalogs/iceberg/namespaces/default/tables/orders/tags")

    assert response.status_code == 200
    assert response.json() == {"tags": []}
```

- [ ] **Step 2: Run tests to verify they fail**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_tags.py -v
```

Expected: FAIL — 404

- [ ] **Step 3: Create the route**

Create `adapter/inbound/web/catalog/list_tags.py`:

```python
"""Define the GET /catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from adapter.inbound.web.catalog.dto import TagResponse, TagsResponse
from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient
from dependencies.catalog import get_catalog_client

router = APIRouter()


@router.get(
    "/catalogs/{catalog}/namespaces/{namespace}/tables/{table}/tags",
    response_model=TagsResponse,
)
def list_tags(
    catalog: str,
    namespace: str,
    table: str,
    client: IcebergCatalogClient = Depends(get_catalog_client),
) -> TagsResponse:
    """Return all tags for a table."""
    tags = client.list_tags(namespace, table)
    return TagsResponse(
        tags=[TagResponse(**t) for t in tags],
    )
```

- [ ] **Step 4: Register route in catalog router**

Update `adapter/inbound/web/catalog/__init__.py` to its final form:

```python
"""Catalog REST API endpoints."""

from fastapi import APIRouter

from adapter.inbound.web.catalog.get_table import router as get_table_router
from adapter.inbound.web.catalog.list_branches import router as list_branches_router
from adapter.inbound.web.catalog.list_namespaces import router as list_namespaces_router
from adapter.inbound.web.catalog.list_snapshots import router as list_snapshots_router
from adapter.inbound.web.catalog.list_tables import router as list_tables_router
from adapter.inbound.web.catalog.list_tags import router as list_tags_router

router = APIRouter(tags=["catalog"])
router.include_router(list_namespaces_router)
router.include_router(list_tables_router)
router.include_router(get_table_router)
router.include_router(list_snapshots_router)
router.include_router(list_branches_router)
router.include_router(list_tags_router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/web/catalog/test_list_tags.py -v
```

Expected: 2 passed

- [ ] **Step 6: Run full validation**

Run:
```bash
uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check .
```

Expected: all tests pass, all architecture contracts pass, no lint errors

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/adapter/inbound/web/catalog/ src/table-maintenance/backend/tests/adapter/inbound/web/catalog/test_list_tags.py
git commit -m "feat(catalog): add GET /tags endpoint"
```
