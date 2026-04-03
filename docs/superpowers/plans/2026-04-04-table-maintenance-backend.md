# Table Maintenance Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI backend at `src/table-maintenance/backend/` that exposes CRUD REST endpoints for managing Iceberg table maintenance jobs as `SparkApplication` / `ScheduledSparkApplication` K8S custom resources.

**Architecture:** Thin FastAPI wrapper over the K8S `CustomObjectsApi`. Reuses Pydantic config models from the existing `jobs/` package (installed as a local dependency). K8S client auto-selects in-cluster config with kubeconfig fallback.

**Tech Stack:** FastAPI, kubernetes Python client, Pydantic v2, uv, pytest, httpx

---

## File Map

```
src/table-maintenance/backend/
├── pyproject.toml
├── Dockerfile
├── main.py                      # FastAPI app, lifespan, dependency wiring
├── config.py                    # AppSettings (namespace, image, etc.)
├── models/
│   ├── __init__.py
│   ├── requests.py              # JobRequest with model_validator
│   └── responses.py            # JobStatus enum, JobResponse
├── k8s/
│   ├── __init__.py
│   ├── client.py                # load_k8s_config() auto-detect
│   ├── manifest.py              # build_manifest() → K8S dict
│   └── jobs_repo.py             # JobsRepository CRUD
├── api/
│   ├── __init__.py
│   └── routes/
│       ├── __init__.py
│       └── jobs.py              # /jobs router
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_manifest.py
    ├── test_jobs_repo.py
    └── test_routes_jobs.py
```

---

## Task 1: Scaffold project

**Files:**
- Create: `src/table-maintenance/backend/pyproject.toml`
- Create: `src/table-maintenance/backend/main.py`
- Create: `src/table-maintenance/backend/models/__init__.py`
- Create: `src/table-maintenance/backend/k8s/__init__.py`
- Create: `src/table-maintenance/backend/api/__init__.py`
- Create: `src/table-maintenance/backend/api/routes/__init__.py`
- Create: `src/table-maintenance/backend/tests/conftest.py`
- Test: `src/table-maintenance/backend/tests/test_health.py`

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p src/table-maintenance/backend/{models,k8s,api/routes,tests}
touch src/table-maintenance/backend/models/__init__.py \
      src/table-maintenance/backend/k8s/__init__.py \
      src/table-maintenance/backend/api/__init__.py \
      src/table-maintenance/backend/api/routes/__init__.py \
      src/table-maintenance/backend/tests/__init__.py
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
# src/table-maintenance/backend/pyproject.toml
[project]
name = "table-maintenance-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi[standard]>=0.115",
    "kubernetes>=32.0",
    "jobs @ file:../jobs",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "httpx>=0.27",
    "pytest-mock>=3",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 3: Write the failing health test**

```python
# src/table-maintenance/backend/tests/test_health.py
from fastapi.testclient import TestClient
from main import app

def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Create minimal `main.py`**

```python
# src/table-maintenance/backend/main.py
from fastapi import FastAPI

app = FastAPI(title="Table Maintenance Backend")


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: Create empty `tests/conftest.py`**

```python
# src/table-maintenance/backend/tests/conftest.py
```

- [ ] **Step 6: Install dependencies and run test**

```bash
cd src/table-maintenance/backend && uv sync --dev
uv run pytest tests/test_health.py -v
```

Expected:
```
tests/test_health.py::test_health PASSED
```

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/
git commit -m "feat(table-maintenance): scaffold backend project"
```

---

## Task 2: AppSettings

**Files:**
- Create: `src/table-maintenance/backend/config.py`
- Test: `src/table-maintenance/backend/tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# src/table-maintenance/backend/tests/test_config.py
from config import AppSettings


def test_defaults():
    s = AppSettings()
    assert s.namespace == "default"
    assert s.image == "localhost:5000/table-maintenance-jobs:latest"
    assert s.image_pull_policy == "Never"
    assert s.spark_version == "4.0.0"
    assert s.service_account == "spark-operator-spark"


def test_env_override(monkeypatch):
    monkeypatch.setenv("BACKEND_NAMESPACE", "spark-jobs")
    s = AppSettings()
    assert s.namespace == "spark-jobs"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_config.py -v
```

Expected: `ImportError` or `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement `config.py`**

```python
# src/table-maintenance/backend/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BACKEND_")

    namespace: str = "default"
    image: str = "localhost:5000/table-maintenance-jobs:latest"
    image_pull_policy: str = "Never"
    spark_version: str = "4.0.0"
    service_account: str = "spark-operator-spark"
    iceberg_jar: str = (
        "https://repo1.maven.org/maven2/org/apache/iceberg/"
        "iceberg-spark-runtime-4.0_2.13/1.10.1/"
        "iceberg-spark-runtime-4.0_2.13-1.10.1.jar"
    )
    iceberg_aws_jar: str = (
        "https://repo1.maven.org/maven2/org/apache/iceberg/"
        "iceberg-aws-bundle/1.10.1/iceberg-aws-bundle-1.10.1.jar"
    )
```

- [ ] **Step 4: Run tests**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_config.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/config.py \
        src/table-maintenance/backend/tests/test_config.py
git commit -m "feat(table-maintenance): add AppSettings"
```

---

## Task 3: Response models

**Files:**
- Create: `src/table-maintenance/backend/models/responses.py`
- Test: `src/table-maintenance/backend/tests/test_responses.py`

- [ ] **Step 1: Write failing tests**

```python
# src/table-maintenance/backend/tests/test_responses.py
from datetime import datetime, timezone
from models.responses import JobStatus, JobResponse, status_from_k8s
from configs.base import JobType


def test_status_empty_state_is_pending():
    assert status_from_k8s("SparkApplication", "") == JobStatus.PENDING


def test_status_running():
    assert status_from_k8s("SparkApplication", "RUNNING") == JobStatus.RUNNING


def test_status_completed():
    assert status_from_k8s("SparkApplication", "COMPLETED") == JobStatus.COMPLETED


def test_status_failed_states():
    for state in ("FAILED", "SUBMISSION_FAILED", "INVALIDATING"):
        assert status_from_k8s("SparkApplication", state) == JobStatus.FAILED


def test_status_unknown_state():
    assert status_from_k8s("SparkApplication", "WEIRD_STATE") == JobStatus.UNKNOWN


def test_scheduled_app_always_running():
    assert status_from_k8s("ScheduledSparkApplication", "") == JobStatus.RUNNING


def test_job_response_fields():
    r = JobResponse(
        name="table-maintenance-rewrite-data-files-abc123",
        kind="SparkApplication",
        namespace="default",
        job_type=JobType.REWRITE_DATA_FILES,
        status=JobStatus.COMPLETED,
        created_at=datetime(2026, 4, 4, tzinfo=timezone.utc),
    )
    assert r.name == "table-maintenance-rewrite-data-files-abc123"
    assert r.status == JobStatus.COMPLETED
```

- [ ] **Step 2: Run to verify failure**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_responses.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `models/responses.py`**

```python
# src/table-maintenance/backend/models/responses.py
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from configs.base import JobType


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


_STATE_MAP: dict[str, JobStatus] = {
    "RUNNING": JobStatus.RUNNING,
    "COMPLETED": JobStatus.COMPLETED,
    "FAILED": JobStatus.FAILED,
    "SUBMISSION_FAILED": JobStatus.FAILED,
    "INVALIDATING": JobStatus.FAILED,
}


def status_from_k8s(kind: str, state: str) -> JobStatus:
    if kind == "ScheduledSparkApplication":
        return JobStatus.RUNNING
    if not state:
        return JobStatus.PENDING
    return _STATE_MAP.get(state, JobStatus.UNKNOWN)


class JobResponse(BaseModel):
    name: str
    kind: str
    namespace: str
    job_type: JobType
    status: JobStatus
    created_at: datetime
```

- [ ] **Step 4: Run tests**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_responses.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/models/responses.py \
        src/table-maintenance/backend/tests/test_responses.py
git commit -m "feat(table-maintenance): add JobStatus and JobResponse models"
```

---

## Task 4: Request models

**Files:**
- Create: `src/table-maintenance/backend/models/requests.py`
- Test: `src/table-maintenance/backend/tests/test_requests.py`

- [ ] **Step 1: Write failing tests**

```python
# src/table-maintenance/backend/tests/test_requests.py
import pytest
from pydantic import ValidationError

from models.requests import JobRequest
from configs.base import JobType
from configs.jobs.rewrite_data_files import RewriteDataFilesConfig
from configs.jobs.expire_snapshots import ExpireSnapshotsConfig


def test_valid_rewrite_data_files_request():
    req = JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={"spark.sql.catalog.retail.uri": "http://polaris:8181/api/catalog"},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
    )
    assert req.job_type == JobType.REWRITE_DATA_FILES
    assert req.catalog == "retail"
    assert req.rewrite_data_files.table == "inventory.orders"


def test_missing_config_for_job_type_raises():
    with pytest.raises(ValidationError, match="rewrite_data_files"):
        JobRequest(
            job_type=JobType.REWRITE_DATA_FILES,
            catalog="retail",
            spark_conf={},
            # rewrite_data_files is None — should fail validation
        )


def test_wrong_config_for_job_type_raises():
    with pytest.raises(ValidationError):
        JobRequest(
            job_type=JobType.REWRITE_DATA_FILES,
            catalog="retail",
            spark_conf={},
            expire_snapshots=ExpireSnapshotsConfig(table="inventory.orders"),
            # rewrite_data_files is still None — wrong config
        )


def test_cron_field_accepted():
    req = JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
        cron="0 2 * * *",
    )
    assert req.cron == "0 2 * * *"


def test_defaults():
    req = JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
    )
    assert req.driver_memory == "512m"
    assert req.executor_memory == "1g"
    assert req.executor_instances == 1
    assert req.cron is None
```

- [ ] **Step 2: Run to verify failure**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_requests.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `models/requests.py`**

```python
# src/table-maintenance/backend/models/requests.py
from pydantic import BaseModel, model_validator

from configs.base import JobType
from configs.jobs.expire_snapshots import ExpireSnapshotsConfig
from configs.jobs.remove_orphan_files import RemoveOrphanFilesConfig
from configs.jobs.rewrite_data_files import RewriteDataFilesConfig
from configs.jobs.rewrite_manifests import RewriteManifestsConfig


class JobRequest(BaseModel):
    job_type: JobType
    catalog: str
    spark_conf: dict[str, str]

    expire_snapshots: ExpireSnapshotsConfig | None = None
    remove_orphan_files: RemoveOrphanFilesConfig | None = None
    rewrite_data_files: RewriteDataFilesConfig | None = None
    rewrite_manifests: RewriteManifestsConfig | None = None

    driver_memory: str = "512m"
    executor_memory: str = "1g"
    executor_instances: int = 1
    cron: str | None = None

    @model_validator(mode="after")
    def validate_job_config(self) -> "JobRequest":
        mapping = {
            JobType.EXPIRE_SNAPSHOTS: self.expire_snapshots,
            JobType.REMOVE_ORPHAN_FILES: self.remove_orphan_files,
            JobType.REWRITE_DATA_FILES: self.rewrite_data_files,
            JobType.REWRITE_MANIFESTS: self.rewrite_manifests,
        }
        if mapping[self.job_type] is None:
            raise ValueError(
                f"Config for job_type={self.job_type.value!r} must be provided "
                f"(set the '{self.job_type.value}' field)"
            )
        return self
```

- [ ] **Step 4: Run tests**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_requests.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/models/requests.py \
        src/table-maintenance/backend/tests/test_requests.py
git commit -m "feat(table-maintenance): add JobRequest model with validation"
```

---

## Task 5: K8S client

**Files:**
- Create: `src/table-maintenance/backend/k8s/client.py`
- Test: `src/table-maintenance/backend/tests/test_k8s_client.py`

- [ ] **Step 1: Write failing tests**

```python
# src/table-maintenance/backend/tests/test_k8s_client.py
from unittest.mock import patch, MagicMock
from kubernetes.config.config_exception import ConfigException
from k8s.client import load_k8s_config


def test_uses_incluster_when_available():
    with patch("k8s.client.k8s_config.load_incluster_config") as mock_in, \
         patch("k8s.client.k8s_config.load_kube_config") as mock_kube:
        load_k8s_config()
        mock_in.assert_called_once()
        mock_kube.assert_not_called()


def test_falls_back_to_kubeconfig_when_not_in_cluster():
    with patch("k8s.client.k8s_config.load_incluster_config",
               side_effect=ConfigException("not in cluster")), \
         patch("k8s.client.k8s_config.load_kube_config") as mock_kube:
        load_k8s_config()
        mock_kube.assert_called_once()
```

- [ ] **Step 2: Run to verify failure**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_k8s_client.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `k8s/client.py`**

```python
# src/table-maintenance/backend/k8s/client.py
from kubernetes import config as k8s_config
from kubernetes.config.config_exception import ConfigException


def load_k8s_config() -> None:
    """Load K8S config: in-cluster if available, otherwise kubeconfig."""
    try:
        k8s_config.load_incluster_config()
    except ConfigException:
        k8s_config.load_kube_config()
```

- [ ] **Step 4: Run tests**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_k8s_client.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/k8s/client.py \
        src/table-maintenance/backend/tests/test_k8s_client.py
git commit -m "feat(table-maintenance): add K8S config auto-detect"
```

---

## Task 6: Manifest builder

**Files:**
- Create: `src/table-maintenance/backend/k8s/manifest.py`
- Test: `src/table-maintenance/backend/tests/test_manifest.py`

- [ ] **Step 1: Write failing tests**

```python
# src/table-maintenance/backend/tests/test_manifest.py
from datetime import datetime, timezone

from config import AppSettings
from configs.base import JobType
from configs.jobs.expire_snapshots import ExpireSnapshotsConfig
from configs.jobs.rewrite_data_files import RewriteDataFilesConfig, Strategy
from models.requests import JobRequest
from k8s.manifest import build_manifest


SETTINGS = AppSettings()


def _make_rewrite_request(**kwargs) -> JobRequest:
    return JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={"spark.sql.catalog.retail.uri": "http://polaris:8181/api/catalog"},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders", **kwargs),
    )


def test_kind_is_spark_application_without_cron():
    manifest = build_manifest("my-job", _make_rewrite_request(), SETTINGS)
    assert manifest["kind"] == "SparkApplication"
    assert manifest["apiVersion"] == "sparkoperator.k8s.io/v1beta2"


def test_name_and_namespace():
    manifest = build_manifest("my-job-abc123", _make_rewrite_request(), SETTINGS)
    assert manifest["metadata"]["name"] == "my-job-abc123"
    assert manifest["metadata"]["namespace"] == SETTINGS.namespace


def test_spark_conf_mapped():
    manifest = build_manifest("my-job", _make_rewrite_request(), SETTINGS)
    assert manifest["spec"]["sparkConf"]["spark.sql.catalog.retail.uri"] == \
        "http://polaris:8181/api/catalog"


def test_driver_env_glac_vars():
    manifest = build_manifest("my-job", _make_rewrite_request(rewrite_all=True), SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_JOB_TYPE"] == "rewrite_data_files"
    assert env["GLAC_CATALOG"] == "retail"
    assert env["GLAC_REWRITE_DATA_FILES__TABLE"] == "inventory.orders"
    assert env["GLAC_REWRITE_DATA_FILES__REWRITE_ALL"] == "true"


def test_strategy_enum_serialized_as_value():
    req = _make_rewrite_request(strategy=Strategy.SORT)
    manifest = build_manifest("my-job", req, SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_REWRITE_DATA_FILES__STRATEGY"] == "sort"


def test_expire_snapshots_datetime_env():
    dt = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    req = JobRequest(
        job_type=JobType.EXPIRE_SNAPSHOTS,
        catalog="retail",
        spark_conf={},
        expire_snapshots=ExpireSnapshotsConfig(table="inventory.orders", older_than=dt),
    )
    manifest = build_manifest("my-job", req, SETTINGS)
    env = {e["name"]: e["value"] for e in manifest["spec"]["driver"]["env"]}
    assert env["GLAC_EXPIRE_SNAPSHOTS__TABLE"] == "inventory.orders"
    assert "2026-01-01" in env["GLAC_EXPIRE_SNAPSHOTS__OLDER_THAN"]


def test_executor_env_has_aws_vars():
    manifest = build_manifest("my-job", _make_rewrite_request(), SETTINGS)
    exec_env_keys = {e["name"] for e in manifest["spec"]["executor"]["env"]}
    assert "AWS_ACCESS_KEY_ID" in exec_env_keys
    assert "AWS_SECRET_ACCESS_KEY" in exec_env_keys


def test_resource_overrides():
    req = _make_rewrite_request()
    req.driver_memory = "1g"
    req.executor_memory = "2g"
    req.executor_instances = 2
    manifest = build_manifest("my-job", req, SETTINGS)
    assert manifest["spec"]["driver"]["memory"] == "1g"
    assert manifest["spec"]["executor"]["memory"] == "2g"
    assert manifest["spec"]["executor"]["instances"] == 2


def test_cron_creates_scheduled_spark_application():
    req = _make_rewrite_request()
    req.cron = "0 2 * * *"
    manifest = build_manifest("my-job", req, SETTINGS)
    assert manifest["kind"] == "ScheduledSparkApplication"
    assert manifest["spec"]["schedule"] == "0 2 * * *"
    assert "type" in manifest["spec"]["template"]  # SparkApplication spec nested in template


def test_none_fields_not_in_env():
    req = _make_rewrite_request()  # no sort_order, no where, etc.
    manifest = build_manifest("my-job", req, SETTINGS)
    env_names = {e["name"] for e in manifest["spec"]["driver"]["env"]}
    assert "GLAC_REWRITE_DATA_FILES__SORT_ORDER" not in env_names
    assert "GLAC_REWRITE_DATA_FILES__WHERE" not in env_names
```

- [ ] **Step 2: Run to verify failure**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_manifest.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `k8s/manifest.py`**

```python
# src/table-maintenance/backend/k8s/manifest.py
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from configs.base import JobType

if TYPE_CHECKING:
    from config import AppSettings
    from models.requests import JobRequest

_JOB_PREFIX: dict[JobType, str] = {
    JobType.EXPIRE_SNAPSHOTS: "GLAC_EXPIRE_SNAPSHOTS",
    JobType.REMOVE_ORPHAN_FILES: "GLAC_REMOVE_ORPHAN_FILES",
    JobType.REWRITE_DATA_FILES: "GLAC_REWRITE_DATA_FILES",
    JobType.REWRITE_MANIFESTS: "GLAC_REWRITE_MANIFESTS",
}

_AWS_ENV = [
    {"name": "AWS_ACCESS_KEY_ID", "value": "minio_user"},
    {"name": "AWS_SECRET_ACCESS_KEY", "value": "minio_password"},
    {"name": "AWS_REGION", "value": "dummy-region"},
]


def _model_to_env(prefix: str, model: BaseModel) -> list[dict]:
    result = []
    for field_name, value in model.model_dump(mode="json", exclude_none=True).items():
        env_key = f"{prefix}__{field_name.upper()}"
        env_val = str(value).lower() if isinstance(value, bool) else str(value)
        result.append({"name": env_key, "value": env_val})
    return result


def _build_driver_env(request: JobRequest) -> list[dict]:
    env = [
        {"name": "GLAC_JOB_TYPE", "value": request.job_type.value},
        {"name": "GLAC_CATALOG", "value": request.catalog},
    ]
    config_by_type = {
        JobType.EXPIRE_SNAPSHOTS: request.expire_snapshots,
        JobType.REMOVE_ORPHAN_FILES: request.remove_orphan_files,
        JobType.REWRITE_DATA_FILES: request.rewrite_data_files,
        JobType.REWRITE_MANIFESTS: request.rewrite_manifests,
    }
    prefix = _JOB_PREFIX[request.job_type]
    job_config = config_by_type[request.job_type]
    if job_config:
        env.extend(_model_to_env(prefix, job_config))
    env.extend(_AWS_ENV)
    return env


def _build_spark_app_spec(request: JobRequest, settings: AppSettings, env: list[dict]) -> dict:
    return {
        "type": "Python",
        "pythonVersion": "3",
        "mode": "cluster",
        "image": settings.image,
        "imagePullPolicy": settings.image_pull_policy,
        "mainApplicationFile": "local:///opt/spark/work-dir/main.py",
        "sparkVersion": settings.spark_version,
        "deps": {
            "jars": [settings.iceberg_jar, settings.iceberg_aws_jar],
        },
        "sparkConf": {
            "spark.sql.extensions": (
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
            ),
            "spark.driver.extraJavaOptions": (
                "-Divy.cache.dir=/tmp/.ivy2 -Divy.home=/tmp/.ivy"
            ),
            **request.spark_conf,
        },
        "driver": {
            "cores": 1,
            "memory": request.driver_memory,
            "serviceAccount": settings.service_account,
            "env": env,
        },
        "executor": {
            "cores": 1,
            "instances": request.executor_instances,
            "memory": request.executor_memory,
            "env": _AWS_ENV,
        },
    }


def build_manifest(name: str, request: JobRequest, settings: AppSettings) -> dict:
    env = _build_driver_env(request)
    spark_spec = _build_spark_app_spec(request, settings, env)

    if request.cron:
        return {
            "apiVersion": "sparkoperator.k8s.io/v1beta2",
            "kind": "ScheduledSparkApplication",
            "metadata": {"name": name, "namespace": settings.namespace},
            "spec": {
                "schedule": request.cron,
                "template": spark_spec,
            },
        }

    return {
        "apiVersion": "sparkoperator.k8s.io/v1beta2",
        "kind": "SparkApplication",
        "metadata": {"name": name, "namespace": settings.namespace},
        "spec": spark_spec,
    }
```

- [ ] **Step 4: Run tests**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_manifest.py -v
```

Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/k8s/manifest.py \
        src/table-maintenance/backend/tests/test_manifest.py
git commit -m "feat(table-maintenance): add SparkApplication manifest builder"
```

---

## Task 7: Jobs repository

**Files:**
- Create: `src/table-maintenance/backend/k8s/jobs_repo.py`
- Test: `src/table-maintenance/backend/tests/test_jobs_repo.py`

- [ ] **Step 1: Write failing tests**

```python
# src/table-maintenance/backend/tests/test_jobs_repo.py
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from kubernetes.client.exceptions import ApiException

from config import AppSettings
from configs.base import JobType
from configs.jobs.rewrite_data_files import RewriteDataFilesConfig
from models.requests import JobRequest
from models.responses import JobStatus
from k8s.jobs_repo import JobsRepository


SETTINGS = AppSettings()

MOCK_SPARK_APP = {
    "kind": "SparkApplication",
    "metadata": {
        "name": "table-maintenance-rewrite-data-files-abc123",
        "namespace": "default",
        "creationTimestamp": "2026-04-04T10:00:00Z",
    },
    "spec": {
        "driver": {
            "env": [
                {"name": "GLAC_JOB_TYPE", "value": "rewrite_data_files"},
            ]
        }
    },
    "status": {"applicationState": {"state": "COMPLETED"}},
}


def _make_request() -> JobRequest:
    return JobRequest(
        job_type=JobType.REWRITE_DATA_FILES,
        catalog="retail",
        spark_conf={},
        rewrite_data_files=RewriteDataFilesConfig(table="inventory.orders"),
    )


def test_create_returns_job_response():
    api = MagicMock()
    api.create_namespaced_custom_object.return_value = MOCK_SPARK_APP
    repo = JobsRepository(api, SETTINGS)

    with patch("k8s.jobs_repo._generate_name", return_value="table-maintenance-rewrite-data-files-abc123"):
        response = repo.create(_make_request())

    assert response.name == "table-maintenance-rewrite-data-files-abc123"
    assert response.kind == "SparkApplication"
    assert response.status == JobStatus.COMPLETED
    assert response.job_type == JobType.REWRITE_DATA_FILES
    api.create_namespaced_custom_object.assert_called_once()
    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "sparkapplications"


def test_create_scheduled_uses_correct_plural():
    api = MagicMock()
    scheduled_app = {**MOCK_SPARK_APP, "kind": "ScheduledSparkApplication"}
    api.create_namespaced_custom_object.return_value = scheduled_app
    repo = JobsRepository(api, SETTINGS)

    req = _make_request()
    req.cron = "0 2 * * *"

    with patch("k8s.jobs_repo._generate_name", return_value="my-job"):
        repo.create(req)

    call_kwargs = api.create_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "scheduledsparkapplications"


def test_list_merges_both_kinds():
    api = MagicMock()
    api.list_namespaced_custom_object.side_effect = [
        {"items": [MOCK_SPARK_APP]},
        {"items": []},
    ]
    repo = JobsRepository(api, SETTINGS)
    results = repo.list()
    assert len(results) == 1
    assert api.list_namespaced_custom_object.call_count == 2


def test_get_tries_spark_application_first():
    api = MagicMock()
    api.get_namespaced_custom_object.return_value = MOCK_SPARK_APP
    repo = JobsRepository(api, SETTINGS)

    response = repo.get("table-maintenance-rewrite-data-files-abc123")

    assert response.name == "table-maintenance-rewrite-data-files-abc123"
    first_call = api.get_namespaced_custom_object.call_args_list[0].kwargs
    assert first_call["plural"] == "sparkapplications"


def test_get_falls_back_to_scheduled():
    api = MagicMock()
    scheduled_app = {
        **MOCK_SPARK_APP,
        "kind": "ScheduledSparkApplication",
        "spec": {
            "template": {
                "driver": {
                    "env": [{"name": "GLAC_JOB_TYPE", "value": "rewrite_data_files"}]
                }
            }
        },
    }
    not_found = ApiException(status=404)
    api.get_namespaced_custom_object.side_effect = [not_found, scheduled_app]
    repo = JobsRepository(api, SETTINGS)

    response = repo.get("my-job")
    assert response.kind == "ScheduledSparkApplication"


def test_get_raises_404_when_not_found():
    api = MagicMock()
    api.get_namespaced_custom_object.side_effect = ApiException(status=404)
    repo = JobsRepository(api, SETTINGS)

    with pytest.raises(HTTPException) as exc_info:
        repo.get("nonexistent")
    assert exc_info.value.status_code == 404


def test_delete_calls_correct_plural():
    api = MagicMock()
    api.delete_namespaced_custom_object.return_value = {}
    repo = JobsRepository(api, SETTINGS)

    repo.delete("table-maintenance-rewrite-data-files-abc123")
    call_kwargs = api.delete_namespaced_custom_object.call_args.kwargs
    assert call_kwargs["plural"] == "sparkapplications"


def test_delete_raises_404_when_not_found():
    api = MagicMock()
    api.delete_namespaced_custom_object.side_effect = ApiException(status=404)
    repo = JobsRepository(api, SETTINGS)

    with pytest.raises(HTTPException) as exc_info:
        repo.delete("nonexistent")
    assert exc_info.value.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_jobs_repo.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `k8s/jobs_repo.py`**

```python
# src/table-maintenance/backend/k8s/jobs_repo.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from kubernetes.client.exceptions import ApiException

from configs.base import JobType
from k8s.manifest import build_manifest
from models.responses import JobResponse, JobStatus, status_from_k8s

if TYPE_CHECKING:
    from kubernetes.client import CustomObjectsApi
    from config import AppSettings
    from models.requests import JobRequest

_GROUP = "sparkoperator.k8s.io"
_VERSION = "v1beta2"
_PLURAL_SPARK = "sparkapplications"
_PLURAL_SCHEDULED = "scheduledsparkapplications"


def _generate_name(job_type: JobType) -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"table-maintenance-{job_type.value.replace('_', '-')}-{suffix}"


def _extract_job_type(resource: dict) -> JobType:
    # SparkApplication: spec.driver.env
    for env in resource.get("spec", {}).get("driver", {}).get("env", []):
        if env["name"] == "GLAC_JOB_TYPE":
            return JobType(env["value"])
    # ScheduledSparkApplication: spec.template.driver.env
    for env in (
        resource.get("spec", {})
        .get("template", {})
        .get("driver", {})
        .get("env", [])
    ):
        if env["name"] == "GLAC_JOB_TYPE":
            return JobType(env["value"])
    raise ValueError(f"Cannot determine job_type from resource {resource.get('metadata', {}).get('name')}")


def _to_response(resource: dict, job_type: JobType) -> JobResponse:
    meta = resource.get("metadata", {})
    ts = meta.get("creationTimestamp")
    created_at = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else datetime.utcnow()
    kind = resource.get("kind", "SparkApplication")
    state = resource.get("status", {}).get("applicationState", {}).get("state", "")
    return JobResponse(
        name=meta["name"],
        kind=kind,
        namespace=meta.get("namespace", "default"),
        job_type=job_type,
        status=status_from_k8s(kind, state),
        created_at=created_at,
    )


class JobsRepository:
    def __init__(self, api: CustomObjectsApi, settings: AppSettings):
        self._api = api
        self._settings = settings

    def create(self, request: JobRequest) -> JobResponse:
        name = _generate_name(request.job_type)
        manifest = build_manifest(name, request, self._settings)
        plural = _PLURAL_SCHEDULED if manifest["kind"] == "ScheduledSparkApplication" else _PLURAL_SPARK
        resource = self._api.create_namespaced_custom_object(
            group=_GROUP,
            version=_VERSION,
            namespace=self._settings.namespace,
            plural=plural,
            body=manifest,
        )
        return _to_response(resource, request.job_type)

    def list(self) -> list[JobResponse]:
        results = []
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            resp = self._api.list_namespaced_custom_object(
                group=_GROUP,
                version=_VERSION,
                namespace=self._settings.namespace,
                plural=plural,
            )
            for item in resp.get("items", []):
                try:
                    results.append(_to_response(item, _extract_job_type(item)))
                except ValueError:
                    continue
        return results

    def get(self, name: str) -> JobResponse:
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            try:
                resource = self._api.get_namespaced_custom_object(
                    group=_GROUP,
                    version=_VERSION,
                    namespace=self._settings.namespace,
                    plural=plural,
                    name=name,
                )
                return _to_response(resource, _extract_job_type(resource))
            except ApiException as e:
                if e.status == 404:
                    continue
                raise
        raise HTTPException(status_code=404, detail=f"Job {name!r} not found")

    def delete(self, name: str) -> None:
        for plural in (_PLURAL_SPARK, _PLURAL_SCHEDULED):
            try:
                self._api.delete_namespaced_custom_object(
                    group=_GROUP,
                    version=_VERSION,
                    namespace=self._settings.namespace,
                    plural=plural,
                    name=name,
                )
                return
            except ApiException as e:
                if e.status == 404:
                    continue
                raise
        raise HTTPException(status_code=404, detail=f"Job {name!r} not found")
```

- [ ] **Step 4: Run tests**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_jobs_repo.py -v
```

Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/k8s/jobs_repo.py \
        src/table-maintenance/backend/tests/test_jobs_repo.py
git commit -m "feat(table-maintenance): add JobsRepository CRUD"
```

---

## Task 8: Jobs routes

**Files:**
- Create: `src/table-maintenance/backend/api/routes/jobs.py`
- Test: `src/table-maintenance/backend/tests/test_routes_jobs.py`

- [ ] **Step 1: Write failing tests**

```python
# src/table-maintenance/backend/tests/test_routes_jobs.py
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.jobs import router, get_repo
from configs.base import JobType
from models.responses import JobResponse, JobStatus

SAMPLE_RESPONSE = JobResponse(
    name="table-maintenance-rewrite-data-files-abc123",
    kind="SparkApplication",
    namespace="default",
    job_type=JobType.REWRITE_DATA_FILES,
    status=JobStatus.COMPLETED,
    created_at=datetime(2026, 4, 4, tzinfo=timezone.utc),
)


def _make_client(repo: MagicMock) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repo] = lambda: repo
    return TestClient(app)


def test_post_job_returns_201():
    repo = MagicMock()
    repo.create.return_value = SAMPLE_RESPONSE
    client = _make_client(repo)

    payload = {
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "spark_conf": {},
        "rewrite_data_files": {"table": "inventory.orders"},
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 201
    assert response.json()["name"] == "table-maintenance-rewrite-data-files-abc123"
    assert response.json()["status"] == "completed"


def test_post_job_invalid_request_returns_422():
    repo = MagicMock()
    client = _make_client(repo)

    payload = {
        "job_type": "rewrite_data_files",
        "catalog": "retail",
        "spark_conf": {},
        # missing rewrite_data_files config
    }
    response = client.post("/jobs", json=payload)
    assert response.status_code == 422


def test_list_jobs_returns_200():
    repo = MagicMock()
    repo.list.return_value = [SAMPLE_RESPONSE]
    client = _make_client(repo)

    response = client.get("/jobs")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_job_returns_200():
    repo = MagicMock()
    repo.get.return_value = SAMPLE_RESPONSE
    client = _make_client(repo)

    response = client.get("/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 200
    assert response.json()["kind"] == "SparkApplication"


def test_get_job_not_found_returns_404():
    from fastapi import HTTPException
    repo = MagicMock()
    repo.get.side_effect = HTTPException(status_code=404, detail="Job not found")
    client = _make_client(repo)

    response = client.get("/jobs/nonexistent")
    assert response.status_code == 404


def test_delete_job_returns_204():
    repo = MagicMock()
    repo.delete.return_value = None
    client = _make_client(repo)

    response = client.delete("/jobs/table-maintenance-rewrite-data-files-abc123")
    assert response.status_code == 204


def test_delete_job_not_found_returns_404():
    from fastapi import HTTPException
    repo = MagicMock()
    repo.delete.side_effect = HTTPException(status_code=404, detail="Job not found")
    client = _make_client(repo)

    response = client.delete("/jobs/nonexistent")
    assert response.status_code == 404
```

- [ ] **Step 2: Run to verify failure**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_routes_jobs.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement `api/routes/jobs.py`**

```python
# src/table-maintenance/backend/api/routes/jobs.py
from fastapi import APIRouter, Depends, Response

from k8s.jobs_repo import JobsRepository
from models.requests import JobRequest
from models.responses import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_repo() -> JobsRepository:
    raise NotImplementedError("Dependency not wired — call app.dependency_overrides[get_repo]")


@router.post("", response_model=JobResponse, status_code=201)
def create_job(request: JobRequest, repo: JobsRepository = Depends(get_repo)):
    return repo.create(request)


@router.get("", response_model=list[JobResponse])
def list_jobs(repo: JobsRepository = Depends(get_repo)):
    return repo.list()


@router.get("/{name}", response_model=JobResponse)
def get_job(name: str, repo: JobsRepository = Depends(get_repo)):
    return repo.get(name)


@router.delete("/{name}", status_code=204, response_class=Response)
def delete_job(name: str, repo: JobsRepository = Depends(get_repo)):
    repo.delete(name)
```

- [ ] **Step 4: Run tests**

```bash
cd src/table-maintenance/backend && uv run pytest tests/test_routes_jobs.py -v
```

Expected: `7 passed`

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/api/routes/jobs.py \
        src/table-maintenance/backend/tests/test_routes_jobs.py
git commit -m "feat(table-maintenance): add /jobs REST endpoints"
```

---

## Task 9: Wire main.py + run full suite

**Files:**
- Modify: `src/table-maintenance/backend/main.py`

- [ ] **Step 1: Update `main.py` with lifespan and router**

```python
# src/table-maintenance/backend/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from kubernetes import client as k8s_client

from api.routes.jobs import router as jobs_router, get_repo
from config import AppSettings
from k8s.client import load_k8s_config
from k8s.jobs_repo import JobsRepository

settings = AppSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_k8s_config()
    api = k8s_client.CustomObjectsApi()
    repo = JobsRepository(api, settings)
    app.dependency_overrides[get_repo] = lambda: repo
    yield
    app.dependency_overrides.clear()


app = FastAPI(title="Table Maintenance Backend", lifespan=lifespan)
app.include_router(jobs_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Run full test suite**

```bash
cd src/table-maintenance/backend && uv run pytest -v
```

Expected: all tests pass (health, config, responses, requests, k8s_client, manifest, jobs_repo, routes_jobs)

- [ ] **Step 3: Commit**

```bash
git add src/table-maintenance/backend/main.py
git commit -m "feat(table-maintenance): wire FastAPI lifespan and routes"
```

---

## Task 10: Dockerfile

**Files:**
- Create: `src/table-maintenance/backend/Dockerfile`

> **Note:** The Docker build context must be `src/table-maintenance/` (parent of both `jobs/` and `backend/`) because `jobs/` is a local dependency. Build with:
> `docker build -t table-maintenance-backend -f backend/Dockerfile src/table-maintenance/`

- [ ] **Step 1: Write `Dockerfile`**

```dockerfile
# src/table-maintenance/backend/Dockerfile
# Build context: src/table-maintenance/
FROM python:3.11-slim

RUN pip install --no-cache-dir uv

# Install shared jobs package first (provides configs/ models)
COPY jobs/ /jobs
RUN uv pip install --system --no-cache /jobs

# Install backend dependencies (fastapi, kubernetes, uvicorn)
# jobs is already installed above; enumerate remaining deps directly
WORKDIR /app
COPY backend/ .
RUN uv pip install --system --no-cache \
    "fastapi[standard]>=0.115" \
    "kubernetes>=32.0"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Build image to verify**

```bash
docker build -t table-maintenance-backend:latest \
  -f src/table-maintenance/backend/Dockerfile \
  src/table-maintenance/
```

Expected: build succeeds, no errors

- [ ] **Step 3: Smoke test**

```bash
docker run --rm -p 8000:8000 table-maintenance-backend:latest &
sleep 2
curl -s http://localhost:8000/health
```

Expected: `{"status":"ok"}`

```bash
# Clean up
docker stop $(docker ps -q --filter ancestor=table-maintenance-backend:latest)
```

- [ ] **Step 4: Commit**

```bash
git add src/table-maintenance/backend/Dockerfile
git commit -m "feat(table-maintenance): add backend Dockerfile"
```
