# Table Maintenance Backend — Design Spec

**Date:** 2026-04-04
**Status:** Approved

---

## Overview

A FastAPI backend that exposes a REST API for submitting and managing Iceberg table maintenance jobs on Kubernetes. Each job maps to a `SparkApplication` (one-shot) or `ScheduledSparkApplication` (cron) custom resource managed by the Spark Operator.

---

## Architecture

```
src/table-maintenance/
├── jobs/                        # existing Spark job package (shared)
│   ├── configs/
│   │   ├── base.py              # JobType enum
│   │   ├── job_settings.py      # JobSettings
│   │   └── jobs/                # ExpireSnapshotsConfig, RemoveOrphanFilesConfig,
│   │                            # RewriteDataFilesConfig, RewriteManifestsConfig
│   └── pyproject.toml
│
└── backend/                     # new FastAPI backend
    ├── pyproject.toml           # deps: fastapi, kubernetes, jobs @ file:../jobs
    ├── Dockerfile
    ├── main.py                  # FastAPI app + lifespan (K8S client init)
    ├── config.py                # AppSettings: namespace, image, image_pull_policy
    ├── models/
    │   ├── requests.py          # JobRequest (reuses jobs/ config models)
    │   └── responses.py        # JobResponse, JobStatus enum
    ├── k8s/
    │   ├── client.py            # auto-select in-cluster vs kubeconfig
    │   ├── manifest.py          # JobRequest → SparkApplication/ScheduledSparkApplication dict
    │   └── jobs_repo.py         # CRUD via CustomObjectsApi
    └── api/
        └── routes/
            └── jobs.py          # all /jobs endpoints
```

### Shared package dependency

`backend/pyproject.toml` declares `jobs @ file:../jobs`. This allows the backend to import `JobType`, `ExpireSnapshotsConfig`, `RewriteDataFilesConfig`, etc. directly — no model duplication.

---

## API

### Endpoints

| Method   | Path          | Description                                        |
|----------|---------------|----------------------------------------------------|
| `POST`   | `/jobs`       | Create SparkApplication or ScheduledSparkApplication |
| `GET`    | `/jobs`       | List all jobs (both kinds)                         |
| `GET`    | `/jobs/{name}`| Get a single job's status                          |
| `DELETE` | `/jobs/{name}`| Delete the K8S resource (tries SparkApplication first, falls back to ScheduledSparkApplication) |

### Request Model — `JobRequest`

```python
class JobRequest(BaseModel):
    job_type: JobType                              # expire_snapshots | remove_orphan_files
                                                   # | rewrite_data_files | rewrite_manifests
    catalog: str                                   # Spark catalog name, e.g. "retail"
    spark_conf: dict[str, str]                     # arbitrary Spark config entries
                                                   # (catalog URI, MinIO endpoint, credentials…)

    # exactly one of these should be set, matching job_type
    expire_snapshots: ExpireSnapshotsConfig | None = None
    remove_orphan_files: RemoveOrphanFilesConfig | None = None
    rewrite_data_files: RewriteDataFilesConfig | None = None
    rewrite_manifests: RewriteManifestsConfig | None = None

    # resource overrides
    driver_memory: str = "512m"
    executor_memory: str = "1g"
    executor_instances: int = 1

    # optional: if set, creates ScheduledSparkApplication
    cron: str | None = None
```

Validation: the config field matching `job_type` must be non-null (enforced via `model_validator`).

### Response Model — `JobResponse`

```python
class JobStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"
    UNKNOWN   = "unknown"

class JobResponse(BaseModel):
    name: str          # auto-generated K8S resource name
    kind: str          # "SparkApplication" | "ScheduledSparkApplication"
    namespace: str
    job_type: JobType
    status: JobStatus
    created_at: datetime
```

---

## K8S Resource Naming

```
table-maintenance-{job_type_with_dashes}-{uuid8}
# e.g. table-maintenance-rewrite-data-files-a3f2b1c0
```

Namespace is fixed from `AppSettings.namespace` (default: `default`).

---

## Manifest Builder

`k8s/manifest.py` converts `JobRequest` into a K8S resource dict.

**Env var mapping** — follows the existing `GLAC_*` convention from `jobs/`:

```
GLAC_JOB_TYPE        ← job_type
GLAC_CATALOG         ← catalog
GLAC_{JOB_TYPE}__{FIELD}  ← per-job config fields (nested pydantic → env var)
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION  ← from spark_conf or defaults
```

**sparkConf mapping** — `spark_conf` dict maps 1:1 to `spec.sparkConf`.

**Cron branch** — when `cron` is set, the SparkApplication spec is nested inside a `ScheduledSparkApplication`:

```yaml
kind: ScheduledSparkApplication
spec:
  schedule: "<cron expression>"
  template:
    <SparkApplication spec>
```

---

## K8S Client

`k8s/client.py` tries `config.load_incluster_config()` first; on failure falls back to `config.load_kube_config()`. Returns a shared `CustomObjectsApi` instance, initialized once in FastAPI's lifespan.

---

## Status Mapping

K8S `.status.applicationState.state` → `JobStatus`:

| K8S state | `JobStatus` |
|-----------|-------------|
| `""` / missing | `pending` |
| `RUNNING` | `running` |
| `COMPLETED` | `completed` |
| `FAILED`, `SUBMISSION_FAILED`, `INVALIDATING` | `failed` |
| `ScheduledSparkApplication` (no terminal state) | `running` |
| anything else | `unknown` |

---

## GET /jobs — listing both kinds

Calls `CustomObjectsApi.list_namespaced_custom_object` twice:
1. `sparkapplications.sparkoperator.k8s.io`
2. `scheduledsparkapplications.sparkoperator.k8s.io`

Results are merged and returned as a list of `JobResponse`.

---

## AppSettings (`config.py`)

```python
class AppSettings(BaseSettings):
    namespace: str = "default"
    image: str = "localhost:5000/table-maintenance-jobs:latest"
    image_pull_policy: str = "Never"
    spark_version: str = "4.0.0"
    service_account: str = "spark-operator-spark"
    iceberg_jar: str = "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-4.0_2.13/1.10.1/iceberg-spark-runtime-4.0_2.13-1.10.1.jar"
    iceberg_aws_jar: str = "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.1/iceberg-aws-bundle-1.10.1.jar"
```

---

## Error Handling

| Scenario | HTTP status |
|----------|-------------|
| Job not found | 404 |
| K8S conflict (name already exists) | 409 |
| Validation error (wrong config for job_type) | 422 |
| K8S API unreachable | 503 |

---

## Out of Scope

- Authentication / authorization
- Persisting job history beyond what K8S stores
- Log streaming (GET /jobs/{name}/logs)
- Web UI
