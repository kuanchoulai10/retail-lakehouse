# Job Run Completion Callback Design

## Context

After a job run is submitted to K8s (SparkApplication), the backend has no mechanism to learn whether it succeeded or failed. The `job_runs` table stays PENDING forever. The frontend cannot display results.

Future runtimes (e.g. Trino via Python client) will have different execution models. The design must accommodate both ephemeral K8s pods (Spark) and synchronous query clients (Trino) behind a unified abstraction.

## Decision: Runtime Callback to Backend API

The runtime calls the backend's REST API to report completion. This follows the same pattern as Airflow's Execution API, where workers report state via HTTP rather than writing to the database directly.

**Why callback over polling:**
- Trino queries complete synchronously within the backend process — no external observer needed. The gateway itself calls the same completion use case.
- Spark pods call back when done — immediate, no polling delay.
- Runtime stays decoupled from the DB schema. All state transitions go through the domain model's state machine guards and emit domain events via the outbox.

**Why callback over runtime writing directly to DB:**
- Preserves aggregate integrity — `JobRun.complete()` and `JobRun.fail()` enforce the state machine.
- Domain events (`JobRunCompleted`, `JobRunFailed`) are emitted to the outbox for downstream consumers.
- Single writer to the `job_runs` table — no race conditions between backend and runtime.

## Domain Model Changes

### JobRunResult (new value object)

```python
@dataclass(frozen=True)
class JobRunResult(ValueObject):
    duration_ms: int | None
    metadata: dict[str, str]   # flexible key-value, each runtime/job type defines its own keys
```

- `metadata` stores runtime-specific data as `dict[str, str]`.
  - Spark expire_snapshots: `{"expired_snapshots": "42", "deleted_files": "15"}`
  - Spark rewrite_data_files: `{"rewritten_files": "10", "added_files": "3"}`
  - Future Trino: `{"query_id": "...", "rows_returned": "100"}`
- Stored as JSONB in the database.
- No `rows_affected` first-class field — Iceberg maintenance procedures return different schemas per job type. All result data goes into `metadata`.

### JobRun Aggregate (modifications)

New field:
- `result: JobRunResult | None`

New behavior — `complete(result)`:
- Guard: must be RUNNING.
- Sets `status = COMPLETED`, `finished_at = now()`, `result = result`.
- Registers `JobRunCompleted` domain event.

New behavior — `fail(error, result=None)`:
- Guard: must be RUNNING (or PENDING for submit failures).
- Sets `status = FAILED`, `finished_at = now()`, `result = result`.
- Registers `JobRunFailed` domain event with error message.

### Domain Events (modifications)

- `JobRunCompleted`: add `result: JobRunResult`.
- `JobRunFailed`: add `error: str`, `result: JobRunResult | None`.

### State Machine (complete)

```
PENDING  → RUNNING      (submit succeeds)
PENDING  → FAILED       (submit itself fails)
PENDING  → CANCELLED    (manual cancel)
RUNNING  → COMPLETED    (runtime callback: success)
RUNNING  → FAILED       (runtime callback: failure)
RUNNING  → CANCELLED    (manual cancel)
```

## Application Layer: Two New Use Cases

### CompleteJobRun

```
Port Inbound:
  CompleteJobRun(UseCase[CompleteJobRunInput, CompleteJobRunOutput])

  CompleteJobRunInput:
    run_id: str
    duration_ms: int | None
    metadata: dict[str, str] | None

  CompleteJobRunOutput:
    run_id: str
    status: str
    finished_at: str

Service (CompleteJobRunService):
  1. job_runs_repo.get(run_id)
  2. Build JobRunResult from input fields
  3. job_run.complete(result)
  4. job_runs_repo.save(job_run)
  5. outbox_store.append(job_run.collect_events())
```

### FailJobRun

```
Port Inbound:
  FailJobRun(UseCase[FailJobRunInput, FailJobRunOutput])

  FailJobRunInput:
    run_id: str
    error: str
    duration_ms: int | None
    metadata: dict[str, str] | None

  FailJobRunOutput:
    run_id: str
    status: str
    finished_at: str

Service (FailJobRunService):
  1. job_runs_repo.get(run_id)
  2. Build JobRunResult from input fields (if present)
  3. job_run.fail(error, result)
  4. job_runs_repo.save(job_run)
  5. outbox_store.append(job_run.collect_events())
```

## Adapter Layer: Callback API Endpoints

### Endpoints

```
POST /runs/{run_id}/complete
  Request Body:
    duration_ms: int | null
    metadata: dict[str, str] | null

  Response 200:
    run_id: str
    status: "completed"
    finished_at: str

POST /runs/{run_id}/fail
  Request Body:
    error: str
    duration_ms: int | null
    metadata: dict[str, str] | null

  Response 200:
    run_id: str
    status: "failed"
    finished_at: str
```

### File Structure

```
adapter/inbound/web/job_run/
├── trigger_job_run.py      # existing
├── get_job_run.py          # existing
├── list_job_runs.py        # existing
├── complete_job_run.py     # new
└── fail_job_run.py         # new
```

Authentication: deferred. These endpoints are called by runtime pods within the K8s cluster. Auth will be added later.

## Submit Flow Modification

`SubmitJobRunService` currently submits to the gateway and returns. It must now also transition the JobRun to RUNNING:

```
SubmitJobRunService (modified):
  1. gateway.submit(input)
  2. job_run = job_runs_repo.get(run_id)
  3. job_run.start()                              # PENDING → RUNNING
  4. job_runs_repo.save(job_run)
  5. outbox_store.append(job_run.collect_events()) # JobRunStarted event
```

If `gateway.submit()` throws, the JobRun stays PENDING (or transitions to FAILED).

## DB Schema Changes

Existing `job_runs` table — add columns:

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `error` | TEXT | YES | Error message on failure |
| `result_duration_ms` | INTEGER | YES | Execution duration in milliseconds |
| `result_metadata` | JSONB | YES | Runtime-specific key-value result data |

No separate `job_run_results` table. Result is part of the JobRun aggregate.

## Runtime Changes

### Spark runtime (`runtime/spark/`)

**main.py modification:**

```python
def main():
    settings = JobSettings()
    sql = IcebergCallBuilder(settings).build_sql()
    spark = SparkSession.builder.getOrCreate()

    try:
        start = time.time()
        result = spark.sql(sql)
        duration_ms = int((time.time() - start) * 1000)
        rows = result.collect()
        metadata = extract_metadata(settings.job_type, rows)

        report_complete(
            callback_base_url=settings.callback_base_url,
            run_id=settings.run_id,
            duration_ms=duration_ms,
            metadata=metadata,
        )
    except Exception as e:
        report_fail(
            callback_base_url=settings.callback_base_url,
            run_id=settings.run_id,
            error=str(e),
        )
```

**New file — `callback.py`:**
- `report_complete(callback_base_url, run_id, duration_ms, metadata)` — POST to `/runs/{run_id}/complete`
- `report_fail(callback_base_url, run_id, error, ...)` — POST to `/runs/{run_id}/fail`
- Retry: 3 attempts with exponential backoff. If all fail, the pod exits with non-zero code (result is lost; operator must check K8s logs).

**JobSettings additions:**
- `run_id: str` — from `GLAC_RUN_ID` env var
- `callback_base_url: str` — from `GLAC_CALLBACK_BASE_URL` env var

**K8s manifest changes:**
- `SubmitJobRunGateway` (K8s adapter) adds `GLAC_RUN_ID` and `GLAC_CALLBACK_BASE_URL` to the SparkApplication env vars.

### Metadata extraction

Each job type extracts different fields from the Spark SQL result DataFrame:

- `expire_snapshots` → expired snapshot/file counts
- `remove_orphan_files` → removed file count/paths
- `rewrite_data_files` → rewritten/added file counts
- `rewrite_manifests` → rewritten manifest count

Implementation: `extract_metadata(job_type, rows)` function that switches on job type and extracts relevant fields as `dict[str, str]`.

## Complete Data Flow

```
POST /jobs/{name}/runs
  → TriggerJobRun → outbox(JobTriggered)
  → JobTriggeredHandler → create PENDING JobRun → outbox(JobRunCreated)
  → JobRunCreatedHandler → SubmitJobRunService
      → gateway.submit() → K8s SparkApplication
          (env: GLAC_RUN_ID, GLAC_CALLBACK_BASE_URL)
      → job_run.start() → RUNNING → outbox(JobRunStarted)

K8s Pod runs Spark SQL
  → success: POST /runs/{run_id}/complete { duration_ms, metadata }
      → CompleteJobRunService → job_run.complete(result) → COMPLETED
      → outbox(JobRunCompleted)
  → failure: POST /runs/{run_id}/fail { error }
      → FailJobRunService → job_run.fail(error) → FAILED
      → outbox(JobRunFailed)

Frontend
  → GET /runs/{run_id} → status + result (user refreshes to see update)
```

## Frontend

No changes to frontend polling or WebSocket. Users refresh the page to see the latest job run status and result. The existing `GET /runs/{run_id}` endpoint returns the updated status, result metadata, and error (if any).

## Scope Exclusions

- Authentication/authorization for callback endpoints (deferred).
- Safety-net polling for stuck RUNNING jobs (can be added later as a separate feature).
- Trino runtime implementation (future work; the gateway + use case structure supports it).
- WebSocket/SSE for real-time frontend updates.
