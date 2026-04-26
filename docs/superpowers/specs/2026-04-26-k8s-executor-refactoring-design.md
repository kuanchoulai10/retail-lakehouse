# K8s Executor Refactoring & Event Chain Wiring

Date: 2026-04-26

## Problem

`JobRunK8sExecutor` conflates domain entity creation with K8s submission. The outbox event chain breaks after `JobRunCreated` — no handler consumes it to trigger the actual SparkApplication. Per-job resource configuration (cpu, memory) has no domain model; all values are hard-coded in system settings. The K8s adapter layer has duplicated constants, direct bootstrap imports, and a read-only `JobRunsK8sRepo` that fakes a full `JobRunsRepo` interface.

## Decisions

- **Scope**: Full K8s adapter cleanup — executor refactoring, event chain wiring, per-job ResourceConfig, K8s repo removal.
- **Per-job config**: Modeled as `ResourceConfig` value object on the Job entity, not mixed into `job_config` dict.
- **Event self-sufficiency**: `JobTriggered` and `JobRunCreated` carry all information needed by downstream handlers. No repo lookback.
- **Two-hop triggering**: `JobTriggered` → create PENDING JobRun → `JobRunCreated` → submit to K8s. Transactional outbox guarantees at-least-once delivery.
- **K8s repo**: Removed. JobRun state lives in SQL DB. K8s status reconciliation is a future concern.
- **SQL schema for ResourceConfig**: Expanded columns (`driver_memory`, `executor_memory`, `executor_instances`), not JSON blob.

## Design

### 1. Domain Layer

#### 1a. `ResourceConfig` value object (new)

File: `application/domain/model/job/resource_config.py`

```python
@dataclass(frozen=True)
class ResourceConfig(ValueObject):
    driver_memory: str = "512m"
    executor_memory: str = "1g"
    executor_instances: int = 1
```

Frozen dataclass extending `ValueObject`. Provides sensible defaults — optional when creating a Job. Future-extensible with `driver_cores`, `executor_cores`, etc.

#### 1b. `Job` entity gains `resource_config`

```python
@dataclass(eq=False)
class Job(AggregateRoot[JobId]):
    ...
    resource_config: ResourceConfig = field(default_factory=ResourceConfig)
```

- `Job.create()` factory accepts optional `resource_config`.
- `Job.apply_changes()` can modify `resource_config`, tracking changes via `FieldChange`.

#### 1c. `JobTriggered` event enriched

```python
@dataclass(frozen=True)
class JobTriggered(DomainEvent):
    job_id: JobId
    trigger_type: TriggerType
    job_type: JobType
    table_ref: TableReference
    job_config: dict
    resource_config: ResourceConfig
    cron: CronExpression | None
```

`Job.trigger()` populates all fields from its own state.

#### 1d. `JobRunCreated` event enriched

```python
@dataclass(frozen=True)
class JobRunCreated(DomainEvent):
    run_id: JobRunId
    job_id: JobId
    trigger_type: TriggerType
    job_type: JobType
    table_ref: TableReference
    job_config: dict
    resource_config: ResourceConfig
    cron: CronExpression | None
```

Produced by `JobTriggeredHandler`, forwarding Job info from the incoming `JobTriggered` event.

### 2. Application Layer

#### 2a. `JobSubmission` value object (new)

File: `application/port/outbound/job_run/job_submission.py`

```python
@dataclass(frozen=True)
class JobSubmission(ValueObject):
    run_id: str
    job_id: str
    job_type: str
    catalog: str
    table: str
    job_config: dict
    driver_memory: str
    executor_memory: str
    executor_instances: int
    cron_expression: str | None
```

All primitive types. Executor adapters need zero domain imports.

#### 2b. `JobRunExecutor` port redefined

File: `application/port/outbound/job_run/job_run_executor.py`

```python
class JobRunExecutor(ABC):
    @abstractmethod
    def submit(self, submission: JobSubmission) -> None: ...
```

Changed from `trigger(job) -> JobRun` to `submit(submission) -> None`. Executor is a pure side-effect adapter — no entity creation, no return value.

#### 2c. `JobTriggeredHandler` adjusted

Receives enriched `JobTriggered`. Creates PENDING `JobRun` via `JobRun.create()`. Produces enriched `JobRunCreated` event (forwarding job_type, table_ref, job_config, resource_config, cron from the incoming event). Persists JobRun and writes events to outbox.

Dependencies (unchanged): `job_runs_repo`, `outbox_repo`, `serializer`.

#### 2d. `JobRunCreatedHandler` (new)

File: `application/service/job_run/job_run_created_handler.py`

```python
class JobRunCreatedHandler(EventHandler[JobRunCreated]):
    def __init__(self, executor: JobRunExecutor) -> None:
        self._executor = executor

    def handle(self, event: JobRunCreated) -> None:
        submission = JobSubmission(
            run_id=event.run_id.value,
            job_id=event.job_id.value,
            job_type=event.job_type.value,
            catalog=event.table_ref.catalog,
            table=event.table_ref.table,
            job_config=event.job_config,
            driver_memory=event.resource_config.driver_memory,
            executor_memory=event.resource_config.executor_memory,
            executor_instances=event.resource_config.executor_instances,
            cron_expression=event.cron.expression if event.cron else None,
        )
        self._executor.submit(submission)
```

Single responsibility: map event to `JobSubmission`, call executor.

### 3. Adapter Layer

#### 3a. K8s shared constants (new)

File: `adapter/outbound/job_run/k8s/constants.py`

```python
GROUP = "sparkoperator.k8s.io"
VERSION = "v1beta2"
PLURAL_SPARK = "sparkapplications"
PLURAL_SCHEDULED = "scheduledsparkapplications"
JOB_LABEL = "table-maintenance/job-id"
```

Eliminates duplication between executor and repo files.

#### 3b. `K8sExecutorConfig` (new)

File: `adapter/outbound/job_run/k8s/k8s_executor_config.py`

```python
@dataclass(frozen=True)
class K8sExecutorConfig:
    namespace: str
    image: str
    image_pull_policy: str
    spark_version: str
    service_account: str
    iceberg_jar: str
    iceberg_aws_jar: str
```

System-level config only. Adapter-internal — no bootstrap dependency. Bootstrap converts `AppSettings.k8s` into this at composition time.

#### 3c. `JobRunK8sExecutor` rewritten

```python
class JobRunK8sExecutor(JobRunExecutor):
    def __init__(self, api: CustomObjectsApi, config: K8sExecutorConfig) -> None:
        self._api = api
        self._config = config

    def submit(self, submission: JobSubmission) -> None:
        manifest = build_manifest(submission, self._config)
        plural = PLURAL_SCHEDULED if submission.cron_expression else PLURAL_SPARK
        self._api.create_namespaced_custom_object(
            group=GROUP, version=VERSION,
            namespace=self._config.namespace,
            plural=plural, body=manifest,
        )
```

Receives `JobSubmission` + `K8sExecutorConfig`. No domain entity creation, no ID generation.

#### 3d. `build_manifest` rewritten

Signature changes from `build_manifest(job, name, settings)` to `build_manifest(submission, config)`:

- Per-job values (memory, instances, job_config) read from `JobSubmission`.
- System values (image, namespace, spark_version) read from `K8sExecutorConfig`.

#### 3e. `JobRunInMemoryExecutor` updated

```python
class JobRunInMemoryExecutor(JobRunExecutor):
    def __init__(self) -> None:
        self.submitted: list[JobSubmission] = []

    def submit(self, submission: JobSubmission) -> None:
        self.submitted.append(submission)
```

No entity creation, no ID generation. Records submissions for test assertions.

#### 3f. Deletions

| File | Reason |
|------|--------|
| `adapter/outbound/job_run/k8s/job_runs_k8s_repo.py` | JobRun CRUD via SQL repo; K8s repo removed |
| `adapter/outbound/job_run/k8s/status_mapper.py` | Only served K8s repo |
| Related tests for the above | No longer applicable |
| `JobRunsRepoAdapter.K8S` in bootstrap/configs (if exists) | No K8s repo option |

### 4. Bootstrap Layer

#### 4a. `messaging.py` registers new handler

```python
def build_publisher() -> PublisherLoop:
    ...
    # Existing
    dispatcher.register(JobTriggered, JobTriggeredHandler(...))

    # New — wire JobRunCreated → K8s submission
    k8s_config = K8sExecutorConfig(
        namespace=settings.k8s.namespace,
        image=settings.k8s.image,
        ...
    )
    executor = JobRunK8sExecutor(k8s_api, k8s_config)
    dispatcher.register(JobRunCreated, JobRunCreatedHandler(executor))
```

Bootstrap is the only layer that knows all others. Converts `AppSettings.k8s` → `K8sExecutorConfig` here.

#### 4b. `EventSerializer` extended

Handles new fields in `JobTriggered` and `JobRunCreated`:

- `TableReference` → `{"catalog": "...", "table": "..."}`
- `ResourceConfig` → `{"driver_memory": "...", "executor_memory": "...", "executor_instances": ...}`
- `CronExpression | None` → `str | null`
- `JobType` → `str` (StrEnum `.value`)

#### 4c. `K8sSettings` trimmed

Remove per-job fields (`driver_memory`, `executor_memory`, `executor_instances`) — these are now domain defaults in `ResourceConfig`. `K8sSettings` retains only system-level fields: namespace, image, image_pull_policy, spark_version, service_account, iceberg_jar, iceberg_aws_jar.

#### 4d. SQL schema: Job table

`ResourceConfig` stored as expanded columns on the jobs table:

- `driver_memory TEXT DEFAULT '512m'`
- `executor_memory TEXT DEFAULT '1g'`
- `executor_instances INTEGER DEFAULT 1`

Distinct from `job_config` (JSON blob for job-type-specific params). Resource fields are fixed and have domain meaning.

### 5. Event Flow (Complete)

```
User/API                          Scheduler
    │                                │
    │ CreateJobRunService            │ ScheduleJobsService
    │ job.trigger()                  │ job.trigger()
    ▼                                ▼
JobTriggered (enriched) ──► outbox
    │
    ▼
JobTriggeredHandler
    │ 1. Create PENDING JobRun
    │ 2. Persist JobRun to SQL
    │ 3. Write JobRunCreated (enriched) to outbox
    ▼
JobRunCreated (enriched) ──► outbox
    │
    ▼
JobRunCreatedHandler
    │ 1. Map event → JobSubmission
    │ 2. Call executor.submit()
    ▼
JobRunK8sExecutor
    │ build_manifest() → K8s API
    ▼
SparkApplication / ScheduledSparkApplication
```

### 6. Testing Strategy

All changes follow TDD: failing test first, minimal implementation, refactor.

**Domain tests:**
- `ResourceConfig` construction, defaults, equality
- `Job.create()` with `resource_config` — event carries correct info
- `Job.trigger()` — `JobTriggered` includes full Job state
- `Job.apply_changes()` — can modify `resource_config`
- `JobRunCreated` — verify new fields

**Application tests:**
- `JobTriggeredHandler` — enriched `JobTriggered` in, enriched `JobRunCreated` out
- `JobRunCreatedHandler` — `JobRunCreated` in, correct `JobSubmission` passed to executor
- `EventSerializer` — round-trip for enriched events

**Adapter tests:**
- `JobRunK8sExecutor.submit()` — manifest structure, K8s API call params
- `build_manifest` — per-job resource values, system values
- `JobRunInMemoryExecutor.submit()` — records submission

**Integration tests:**
- SQL repo round-trip for Job with `resource_config`
- Import linter — adapter must not import bootstrap
