# Extract Dependencies Module — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a `dependencies/` module as a centralized FastAPI DI composition root, replacing the `_get_use_case` placeholder pattern and simplifying `main.py`.

**Architecture:** The `dependencies/` module sits outside bounded contexts and acts as the composition root — the only place that knows concrete implementations. Route files import dependency providers from here instead of defining placeholder functions. `main.py` is reduced to app factory + lifespan resource management.

**Tech Stack:** FastAPI Depends, pydantic-settings, kubernetes client

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `dependencies/__init__.py` | Package init |
| Create | `dependencies/settings.py` | `get_settings()` — cached AppSettings provider |
| Create | `dependencies/k8s.py` | `get_k8s_api()` — pulls K8s client from app.state |
| Create | `dependencies/repos.py` | `get_jobs_repo()` — assembles repo from K8s API + settings |
| Create | `dependencies/use_cases.py` | `get_*_use_case()` — assembles each service from repo |
| Modify | `jobs/adapter/inbound/web/create_job.py` | Replace `_get_use_case` with `Depends(get_create_job_use_case)` |
| Modify | `jobs/adapter/inbound/web/delete_job.py` | Replace `_get_use_case` with `Depends(get_delete_job_use_case)` |
| Modify | `jobs/adapter/inbound/web/get_job.py` | Replace `_get_use_case` with `Depends(get_get_job_use_case)` |
| Modify | `jobs/adapter/inbound/web/list_jobs.py` | Replace `_get_use_case` with `Depends(get_list_jobs_use_case)` |
| Modify | `main.py` | Simplify to app factory + lifespan (K8s init only) |
| Modify | `tests/test_integration.py` | Override `dependencies/` functions instead of `_get_use_case` |
| Modify | `pyproject.toml` | Add `dependencies*` to setuptools packages |
| Modify | `.importlinter` | Add `dependencies` to root_packages |

---

### Task 1: Verify baseline — all tests green

- [ ] **Step 1: Run the full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests pass (137 tests)

- [ ] **Step 2: Run lint-imports**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`
Expected: 6 contracts kept, 0 broken

---

### Task 2: Create `dependencies/settings.py`

**Files:**
- Create: `src/table-maintenance/backend/dependencies/__init__.py`
- Create: `src/table-maintenance/backend/dependencies/settings.py`
- Test: `src/table-maintenance/backend/tests/dependencies/test_settings.py`

- [ ] **Step 1: Create package init**

```python
# dependencies/__init__.py
```

(Empty file — just marks it as a package.)

- [ ] **Step 2: Write the failing test**

```python
# tests/dependencies/__init__.py
```

```python
# tests/dependencies/test_settings.py
from __future__ import annotations

from dependencies.settings import get_settings
from shared.configs import AppSettings


def test_get_settings_returns_app_settings():
    result = get_settings()
    assert isinstance(result, AppSettings)


def test_get_settings_returns_same_instance():
    a = get_settings()
    b = get_settings()
    assert a is b
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_settings.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dependencies'`

- [ ] **Step 4: Write implementation**

```python
# dependencies/settings.py
from __future__ import annotations

from functools import lru_cache

from shared.configs import AppSettings


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_settings.py -v`
Expected: 2 passed

- [ ] **Step 6: Clear lru_cache between tests**

The `@lru_cache` can leak state between tests. Add a fixture in `tests/dependencies/conftest.py`:

```python
# tests/dependencies/conftest.py
from __future__ import annotations

import pytest

from dependencies.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

- [ ] **Step 7: Run test again to verify**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_settings.py -v`
Expected: 2 passed

- [ ] **Step 8: Commit**

```bash
git add src/table-maintenance/backend/dependencies/ src/table-maintenance/backend/tests/dependencies/
git commit -m "feat(table-maintenance): add dependencies/settings module with cached AppSettings provider"
```

---

### Task 3: Create `dependencies/k8s.py`

**Files:**
- Create: `src/table-maintenance/backend/dependencies/k8s.py`
- Test: `src/table-maintenance/backend/tests/dependencies/test_k8s.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dependencies/test_k8s.py
from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.k8s import get_k8s_api


def test_get_k8s_api_returns_api_from_app_state():
    mock_api = MagicMock()
    mock_request = MagicMock()
    mock_request.app.state.k8s_api = mock_api

    result = get_k8s_api(mock_request)

    assert result is mock_api
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_k8s.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dependencies.k8s'`

- [ ] **Step 3: Write implementation**

```python
# dependencies/k8s.py
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request
    from kubernetes.client import CustomObjectsApi


def get_k8s_api(request: Request) -> CustomObjectsApi:
    return request.app.state.k8s_api
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_k8s.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/dependencies/k8s.py src/table-maintenance/backend/tests/dependencies/test_k8s.py
git commit -m "feat(table-maintenance): add dependencies/k8s module to retrieve K8s API from app state"
```

---

### Task 4: Create `dependencies/repos.py`

**Files:**
- Create: `src/table-maintenance/backend/dependencies/repos.py`
- Test: `src/table-maintenance/backend/tests/dependencies/test_repos.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dependencies/test_repos.py
from __future__ import annotations

from unittest.mock import MagicMock

from dependencies.repos import get_jobs_repo
from jobs.adapter.outbound.k8s.k8s_jobs_repo import K8sJobsRepo
from shared.configs import AppSettings


def test_get_jobs_repo_returns_k8s_jobs_repo():
    mock_api = MagicMock()
    settings = AppSettings()

    result = get_jobs_repo(api=mock_api, settings=settings)

    assert isinstance(result, K8sJobsRepo)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_repos.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dependencies.repos'`

- [ ] **Step 3: Write implementation**

```python
# dependencies/repos.py
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from dependencies.k8s import get_k8s_api
from dependencies.settings import get_settings
from jobs.adapter.outbound.k8s.k8s_jobs_repo import K8sJobsRepo

if TYPE_CHECKING:
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo
    from kubernetes.client import CustomObjectsApi
    from shared.configs import AppSettings


def get_jobs_repo(
    api: CustomObjectsApi = Depends(get_k8s_api),
    settings: AppSettings = Depends(get_settings),
) -> BaseJobsRepo:
    return K8sJobsRepo(api, settings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_repos.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/dependencies/repos.py src/table-maintenance/backend/tests/dependencies/test_repos.py
git commit -m "feat(table-maintenance): add dependencies/repos module to assemble K8sJobsRepo"
```

---

### Task 5: Create `dependencies/use_cases.py`

**Files:**
- Create: `src/table-maintenance/backend/dependencies/use_cases.py`
- Test: `src/table-maintenance/backend/tests/dependencies/test_use_cases.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/dependencies/test_use_cases.py
from __future__ import annotations

from dependencies.use_cases import (
    get_create_job_use_case,
    get_delete_job_use_case,
    get_get_job_use_case,
    get_list_jobs_use_case,
)
from jobs.adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from jobs.application.domain.service.create_job import CreateJobService
from jobs.application.domain.service.delete_job import DeleteJobService
from jobs.application.domain.service.get_job import GetJobService
from jobs.application.domain.service.list_jobs import ListJobsService


def test_get_create_job_use_case():
    repo = InMemoryJobsRepo()
    result = get_create_job_use_case(repo=repo)
    assert isinstance(result, CreateJobService)


def test_get_delete_job_use_case():
    repo = InMemoryJobsRepo()
    result = get_delete_job_use_case(repo=repo)
    assert isinstance(result, DeleteJobService)


def test_get_get_job_use_case():
    repo = InMemoryJobsRepo()
    result = get_get_job_use_case(repo=repo)
    assert isinstance(result, GetJobService)


def test_get_list_jobs_use_case():
    repo = InMemoryJobsRepo()
    result = get_list_jobs_use_case(repo=repo)
    assert isinstance(result, ListJobsService)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_use_cases.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dependencies.use_cases'`

- [ ] **Step 3: Write implementation**

```python
# dependencies/use_cases.py
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from dependencies.repos import get_jobs_repo
from jobs.application.domain.service.create_job import CreateJobService
from jobs.application.domain.service.delete_job import DeleteJobService
from jobs.application.domain.service.get_job import GetJobService
from jobs.application.domain.service.list_jobs import ListJobsService

if TYPE_CHECKING:
    from jobs.application.port.inbound import (
        CreateJobUseCase,
        DeleteJobUseCase,
        GetJobUseCase,
        ListJobsUseCase,
    )
    from jobs.application.port.outbound.jobs_repo import BaseJobsRepo


def get_create_job_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> CreateJobUseCase:
    return CreateJobService(repo)


def get_delete_job_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> DeleteJobUseCase:
    return DeleteJobService(repo)


def get_get_job_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> GetJobUseCase:
    return GetJobService(repo)


def get_list_jobs_use_case(
    repo: BaseJobsRepo = Depends(get_jobs_repo),
) -> ListJobsUseCase:
    return ListJobsService(repo)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/dependencies/test_use_cases.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/dependencies/use_cases.py src/table-maintenance/backend/tests/dependencies/test_use_cases.py
git commit -m "feat(table-maintenance): add dependencies/use_cases module for service assembly"
```

---

### Task 6: Wire routes to use `dependencies/` and simplify `main.py`

This task swaps all four route files, `main.py`, and the integration test in one atomic step — the app won't work in a half-migrated state.

**Files:**
- Modify: `src/table-maintenance/backend/jobs/adapter/inbound/web/create_job.py`
- Modify: `src/table-maintenance/backend/jobs/adapter/inbound/web/delete_job.py`
- Modify: `src/table-maintenance/backend/jobs/adapter/inbound/web/get_job.py`
- Modify: `src/table-maintenance/backend/jobs/adapter/inbound/web/list_jobs.py`
- Modify: `src/table-maintenance/backend/main.py`
- Modify: `src/table-maintenance/backend/tests/test_integration.py`

- [ ] **Step 1: Update `create_job.py`**

Replace the entire file with:

```python
# jobs/adapter/inbound/web/create_job.py
from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies.use_cases import get_create_job_use_case
from jobs.adapter.inbound.web.dto import JobApiRequest, JobApiResponse
from jobs.application.port.inbound import CreateJobInput, CreateJobUseCase

router = APIRouter()


@router.post("/jobs", response_model=JobApiResponse, status_code=201)
def create_job(
    request: JobApiRequest,
    use_case: CreateJobUseCase = Depends(get_create_job_use_case),
):
    result = use_case.execute(
        CreateJobInput(
            job_type=request.job_type,
            catalog=request.catalog,
            expire_snapshots=request.expire_snapshots,
            remove_orphan_files=request.remove_orphan_files,
            rewrite_data_files=request.rewrite_data_files,
            rewrite_manifests=request.rewrite_manifests,
            cron=request.cron,
        )
    )
    return JobApiResponse(
        id=result.id,
        job_type=result.job_type,
        status=result.status,
        created_at=result.created_at,
    )
```

- [ ] **Step 2: Update `delete_job.py`**

Replace the entire file with:

```python
# jobs/adapter/inbound/web/delete_job.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from dependencies.use_cases import get_delete_job_use_case
from jobs.application.exceptions import JobNotFoundError
from jobs.application.port.inbound import DeleteJobInput, DeleteJobUseCase

router = APIRouter()


@router.delete("/jobs/{name}", status_code=204, response_class=Response)
def delete_job(
    name: str,
    use_case: DeleteJobUseCase = Depends(get_delete_job_use_case),
):
    try:
        use_case.execute(DeleteJobInput(job_id=name))
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
```

- [ ] **Step 3: Update `get_job.py`**

Replace the entire file with:

```python
# jobs/adapter/inbound/web/get_job.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from dependencies.use_cases import get_get_job_use_case
from jobs.adapter.inbound.web.dto import JobApiResponse
from jobs.application.exceptions import JobNotFoundError
from jobs.application.port.inbound import GetJobInput, GetJobUseCase

router = APIRouter()


@router.get("/jobs/{name}", response_model=JobApiResponse)
def get_job(
    name: str,
    use_case: GetJobUseCase = Depends(get_get_job_use_case),
):
    try:
        result = use_case.execute(GetJobInput(job_id=name))
        return JobApiResponse(
            id=result.id,
            job_type=result.job_type,
            status=result.status,
            created_at=result.created_at,
        )
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
```

- [ ] **Step 4: Update `list_jobs.py`**

Replace the entire file with:

```python
# jobs/adapter/inbound/web/list_jobs.py
from __future__ import annotations

from fastapi import APIRouter, Depends

from dependencies.use_cases import get_list_jobs_use_case
from jobs.adapter.inbound.web.dto import JobApiResponse
from jobs.application.port.inbound import ListJobsInput, ListJobsUseCase

router = APIRouter()


@router.get("/jobs", response_model=list[JobApiResponse])
def list_jobs(
    use_case: ListJobsUseCase = Depends(get_list_jobs_use_case),
):
    result = use_case.execute(ListJobsInput())
    return [
        JobApiResponse(
            id=item.id,
            job_type=item.job_type,
            status=item.status,
            created_at=item.created_at,
        )
        for item in result.jobs
    ]
```

- [ ] **Step 5: Simplify `main.py`**

Replace the entire file with:

```python
# main.py
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from jobs.adapter.inbound.web import router as jobs_router
from kubernetes import client as k8s_client
from shared.k8s.client import load_k8s_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_k8s_config()
    app.state.k8s_api = k8s_client.CustomObjectsApi()
    yield


app = FastAPI(title="Table Maintenance Backend", lifespan=lifespan)
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Update integration test**

Replace the entire file with:

```python
# tests/test_integration.py
"""Integration test: full CRUD lifecycle via HTTP with InMemoryJobsRepo."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jobs.adapter.inbound.web import router
from jobs.adapter.outbound.in_memory_jobs_repo import InMemoryJobsRepo
from jobs.application.domain.service.create_job import CreateJobService
from jobs.application.domain.service.delete_job import DeleteJobService
from jobs.application.domain.service.get_job import GetJobService
from jobs.application.domain.service.list_jobs import ListJobsService

from dependencies.use_cases import (
    get_create_job_use_case,
    get_delete_job_use_case,
    get_get_job_use_case,
    get_list_jobs_use_case,
)


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    repo = InMemoryJobsRepo()
    app.dependency_overrides[get_create_job_use_case] = lambda: CreateJobService(repo)
    app.dependency_overrides[get_delete_job_use_case] = lambda: DeleteJobService(repo)
    app.dependency_overrides[get_get_job_use_case] = lambda: GetJobService(repo)
    app.dependency_overrides[get_list_jobs_use_case] = lambda: ListJobsService(repo)
    return app


REWRITE_PAYLOAD = {
    "job_type": "rewrite_data_files",
    "catalog": "retail",
    "rewrite_data_files": {"table": "inventory.orders"},
}

EXPIRE_PAYLOAD = {
    "job_type": "expire_snapshots",
    "catalog": "retail",
    "expire_snapshots": {"table": "inventory.orders"},
}


def test_full_crud_lifecycle():
    client = TestClient(_make_app())

    # 1. Empty list at start
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Create first job
    resp = client.post("/v1/jobs", json=REWRITE_PAYLOAD)
    assert resp.status_code == 201
    job1 = resp.json()
    id1 = job1["id"]
    assert len(id1) == 10  # secrets.token_hex(5) produces 10 hex chars
    assert job1["status"] == "pending"

    # 3. List shows 1 job
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == id1

    # 4. Get by id returns the job
    resp = client.get(f"/v1/jobs/{id1}")
    assert resp.status_code == 200
    assert resp.json()["id"] == id1

    # 5. Create second job (different type)
    resp = client.post("/v1/jobs", json=EXPIRE_PAYLOAD)
    assert resp.status_code == 201
    job2 = resp.json()
    id2 = job2["id"]
    assert len(id2) == 10

    # 6. List shows 2 jobs
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    # 7. Delete first job
    resp = client.delete(f"/v1/jobs/{id1}")
    assert resp.status_code == 204

    # 8. List shows 1 job (only second remains)
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == id2

    # 9. Get deleted job returns 404
    resp = client.get(f"/v1/jobs/{id1}")
    assert resp.status_code == 404

    # 10. Delete second job
    resp = client.delete(f"/v1/jobs/{id2}")
    assert resp.status_code == 204

    # 11. List is empty again
    resp = client.get("/v1/jobs")
    assert resp.status_code == 200
    assert resp.json() == []

    # 12. Delete already-deleted job returns 404
    resp = client.delete(f"/v1/jobs/{id2}")
    assert resp.status_code == 404
```

- [ ] **Step 7: Update `pyproject.toml` — add `dependencies` to packages**

In `pyproject.toml`, change:

```toml
[tool.setuptools.packages.find]
include = ["base*", "shared*", "jobs*"]
```

to:

```toml
[tool.setuptools.packages.find]
include = ["base*", "shared*", "jobs*", "dependencies*"]
```

- [ ] **Step 8: Update `.importlinter` — add `dependencies` to root_packages**

In `.importlinter`, change:

```ini
[importlinter]
root_packages =
    jobs
    shared
    base
```

to:

```ini
[importlinter]
root_packages =
    jobs
    shared
    base
    dependencies
```

- [ ] **Step 9: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests pass

- [ ] **Step 10: Run lint-imports**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`
Expected: 6 contracts kept, 0 broken

- [ ] **Step 11: Run ruff**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check .`
Expected: No errors

- [ ] **Step 12: Commit**

```bash
git add src/table-maintenance/backend/
git commit -m "refactor(table-maintenance): replace _get_use_case placeholders with centralized dependencies module"
```
