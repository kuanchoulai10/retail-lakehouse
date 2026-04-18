# Enable Pydocstyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable pydocstyle (D rules) in ruff and add Google-style docstrings to all 600 violations across the backend codebase.

**Architecture:** Layer-by-layer approach — enable D rules with per-file-ignores suppressing all directories, then remove suppressions one layer at a time as docstrings are added. Each layer is one atomic commit.

**Tech Stack:** ruff (pydocstyle rules), Python docstrings (Google convention)

**Worktree:** `/Users/kcl/Projects/retail-lakehouse/.worktrees/enable-pydocstyle`
**Branch:** `feat/enable-pydocstyle`
**Backend root:** `src/table-maintenance/backend/` (all relative paths below are from here)

**Run commands:** Always use `uv run --project <backend-root> --directory <backend-root>` prefix. Never use `cd`.

---

## Conventions

All docstrings follow Google convention (D211 + D212):

```python
"""One-line summary in imperative mood.

Extended description if needed.

Args:
    param_name: Description.

Returns:
    Description.

Raises:
    SomeError: When something goes wrong.
"""
```

- Module docstrings (`D100`): `"""Define the FooBar class."""` or `"""Provide the foo_bar helper."""`
- Package docstrings (`D104`): `"""Job persistence adapters."""`
- Class docstrings (`D101`): `"""In-memory implementation of JobsRepo."""`
- `__init__` docstrings (`D107`): Skip for simple DI constructors (one-line body), add for complex ones. Since ruff requires them, use a minimal one-liner.
- Magic methods (`D105`): `"""Return string representation."""`
- Test functions: `"""Verify that X when Y."""` — one-liner only
- Test classes: `"""Test helper for aggregate root tests."""`
- Fixtures: `"""Provide an in-memory SQLite engine."""`

---

### Task 1: Enable D rules in ruff.toml with per-file-ignores suppression

**Files:**
- Modify: `ruff.toml`

- [ ] **Step 1: Enable D in lint.select**

In `ruff.toml`, replace:
```toml
    #"D", # pydocstyle - not enabled temporarily
```
with:
```toml
    "D",   # pydocstyle - https://docs.astral.sh/ruff/rules/#pydocstyle-d
```

- [ ] **Step 2: Add D203 and D213 to lint.ignore**

Add these two lines to the `lint.ignore` array:
```toml
    "D203",    # no-blank-line-before-class (conflicts with D211)
    "D213",    # multi-line-summary-second-line (conflicts with D212)
```

- [ ] **Step 3: Add pydocstyle convention**

Add after the `[lint.isort]` section:
```toml
[lint.pydocstyle]
convention = "google"
```

- [ ] **Step 4: Add per-file-ignores to suppress D rules for all directories**

Replace the entire `[lint.per-file-ignores]` section with:
```toml
[lint.per-file-ignores]
"tests/*" = ["FA100"]
"src/table-maintenance/backend/base/*" = ["D"]
"src/table-maintenance/backend/application/domain/model/*" = ["D"]
"src/table-maintenance/backend/application/domain/__init__.py" = ["D"]
"src/table-maintenance/backend/application/domain/service/*" = ["D"]
"src/table-maintenance/backend/application/port/*" = ["D"]
"src/table-maintenance/backend/application/exceptions.py" = ["D"]
"src/table-maintenance/backend/adapter/outbound/*" = ["D"]
"src/table-maintenance/backend/adapter/inbound/*" = ["D"]
"src/table-maintenance/backend/adapter/__init__.py" = ["D"]
"src/table-maintenance/backend/configs/*" = ["D"]
"src/table-maintenance/backend/dependencies/*" = ["D"]
"src/table-maintenance/backend/main.py" = ["D"]
"src/table-maintenance/backend/application/__init__.py" = ["D"]
"src/table-maintenance/backend/tests/*" = ["D"]
```

Note: This also removes the three stale per-file-ignores entries referencing old `jobs/` paths.

- [ ] **Step 5: Verify ruff passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check .`
Expected: No errors (all D violations suppressed)

- [ ] **Step 6: Verify tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -q`
Expected: 304 passed

- [ ] **Step 7: Commit**

```bash
git add ruff.toml
git commit -m "feat(lint): enable pydocstyle D rules with per-file-ignores suppression"
```

---

### Task 2: Add docstrings to `base/` layer

**Files (7 modules, ~18 violations):**
- Modify: `base/value_object.py`
- Modify: `base/entity_id.py`
- Modify: `base/entity.py`
- Modify: `base/aggregate_root.py`
- Modify: `base/domain_event.py`
- Modify: `base/repository.py`
- Modify: `base/use_case.py`

These files already have class-level docstrings. Missing: module docstrings (D100), some method docstrings (D102), and magic method docstrings (D105).

- [ ] **Step 1: Add module docstrings (D100)**

Add to the top of each file (before `from __future__` if present, otherwise as first line):

`base/value_object.py`:
```python
"""Define the ValueObject base class."""
```

`base/entity_id.py`:
```python
"""Define the EntityId base class."""
```

`base/entity.py`:
```python
"""Define the Entity base class."""
```

`base/aggregate_root.py`:
```python
"""Define the AggregateRoot base class."""
```

`base/domain_event.py`:
```python
"""Define the DomainEvent base class."""
```

`base/repository.py`:
```python
"""Define the Repository base class."""
```

`base/use_case.py`:
```python
"""Define the UseCase base class."""
```

- [ ] **Step 2: Add method docstrings to Repository**

In `base/repository.py`, add docstrings to the four abstract methods:

```python
@abstractmethod
def create(self, entity: E) -> E:
    """Persist a new entity and return it."""
    ...

@abstractmethod
def get(self, entity_id: EntityId) -> E:
    """Retrieve an entity by its identifier."""
    ...

@abstractmethod
def list_all(self) -> list[E]:
    """Return all entities."""
    ...

@abstractmethod
def delete(self, entity_id: EntityId) -> None:
    """Remove an entity by its identifier."""
    ...
```

- [ ] **Step 3: Add method docstring to UseCase**

In `base/use_case.py`:

```python
@abstractmethod
def execute(self, request: TInput) -> TOutput:
    """Run the use case with the given input."""
    ...
```

- [ ] **Step 4: Add method docstrings to AggregateRoot**

In `base/aggregate_root.py`:

```python
def __init_subclass__(cls, **kwargs: object) -> None:
    """Enforce @dataclass(eq=False) on all subclasses."""
    ...

def register_event(self, event: DomainEvent) -> None:
    """Record a domain event to be published later."""
    ...

def collect_events(self) -> list[DomainEvent]:
    """Return and clear all pending domain events."""
    ...
```

- [ ] **Step 5: Add magic method docstrings to Entity**

In `base/entity.py`:

```python
def __eq__(self, other: object) -> bool:
    """Compare entities by identity, not by attribute values."""
    ...

def __hash__(self) -> int:
    """Hash by entity identity."""
    ...
```

- [ ] **Step 6: Add magic method docstring to EntityId**

In `base/entity_id.py`:

```python
def __str__(self) -> str:
    """Return the raw identifier string."""
    ...
```

- [ ] **Step 7: Remove base/ from per-file-ignores**

In `ruff.toml`, remove this line:
```toml
"src/table-maintenance/backend/base/*" = ["D"]
```

- [ ] **Step 8: Verify ruff passes for base/**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check base/`
Expected: No errors

- [ ] **Step 9: Verify tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/base/ -q`
Expected: All pass

- [ ] **Step 10: Commit**

```bash
git add base/ ruff.toml
git commit -m "docs(base): add docstrings to shared kernel"
```

---

### Task 3: Add docstrings to `application/domain/` layer (models only)

**Files (~44 violations):**
- Modify: `application/domain/__init__.py`
- Modify: `application/domain/model/__init__.py`
- Modify: `application/domain/model/job/__init__.py`
- Modify: `application/domain/model/job/job.py`
- Modify: `application/domain/model/job/job_id.py`
- Modify: `application/domain/model/job/job_type.py`
- Modify: `application/domain/model/job/exceptions.py`
- Modify: `application/domain/model/job_run/__init__.py`
- Modify: `application/domain/model/job_run/job_run.py`
- Modify: `application/domain/model/job_run/job_run_id.py`
- Modify: `application/domain/model/job_run/job_run_status.py`
- Modify: `application/domain/model/job_run/exceptions.py`
- Modify: `application/exceptions.py`
- Modify: `application/__init__.py`

- [ ] **Step 1: Add package docstrings (D104)**

`application/__init__.py`:
```python
"""Application layer for the table-maintenance bounded context."""
```

`application/domain/__init__.py`:
```python
"""Domain model for the table-maintenance bounded context."""
```

`application/domain/model/__init__.py`:
```python
"""Domain entities, value objects, and exceptions."""
```

`application/domain/model/job/__init__.py`:
```python
"""Job aggregate root and related types."""
```

`application/domain/model/job_run/__init__.py`:
```python
"""JobRun aggregate root and related types."""
```

- [ ] **Step 2: Add module docstrings (D100) for job model files**

`application/domain/model/job/job.py`:
```python
"""Define the Job aggregate root."""
```

`application/domain/model/job/job_id.py`:
```python
"""Define the JobId value object."""
```

`application/domain/model/job/job_type.py`:
```python
"""Define the JobType enumeration."""
```

`application/domain/model/job/exceptions.py`:
```python
"""Define domain exceptions for the Job aggregate."""
```

- [ ] **Step 3: Add module docstrings (D100) for job_run model files**

`application/domain/model/job_run/job_run.py`:
```python
"""Define the JobRun aggregate root."""
```

`application/domain/model/job_run/job_run_id.py`:
```python
"""Define the JobRunId value object."""
```

`application/domain/model/job_run/job_run_status.py`:
```python
"""Define the JobRunStatus enumeration."""
```

`application/domain/model/job_run/exceptions.py`:
```python
"""Define domain exceptions for the JobRun aggregate."""
```

- [ ] **Step 4: Add class docstrings where missing**

`application/domain/model/job/job_type.py` — `JobType`:
```python
class JobType(StrEnum):
    """Enumerate the types of table maintenance operations."""
```

`application/domain/model/job_run/job_run_status.py` — `JobRunStatus`:
```python
class JobRunStatus(StrEnum):
    """Enumerate the lifecycle states of a job run execution."""
```

- [ ] **Step 5: Add magic method docstring to Job**

`application/domain/model/job/job.py` — `__post_init__`:
```python
def __post_init__(self) -> None:
    """Initialize job_config to an empty dict if not provided."""
```

- [ ] **Step 6: Add __init__ docstrings to exception classes**

`application/domain/model/job/exceptions.py` — `JobNotFoundError.__init__`:
```python
def __init__(self, name: str) -> None:
    """Initialize with the name of the missing job."""
```

`application/domain/model/job_run/exceptions.py` — `JobRunNotFoundError.__init__`:
```python
def __init__(self, run_id: str) -> None:
    """Initialize with the ID of the missing job run."""
```

- [ ] **Step 7: Add module docstring and __init__ docstrings to application/exceptions.py**

`application/exceptions.py`:
```python
"""Define application-layer exceptions."""
```

Add `__init__` docstrings to all three exception classes:
```python
# JobNotFoundError.__init__
"""Initialize with the ID of the missing job."""

# JobRunNotFoundError.__init__
"""Initialize with the ID of the missing job run."""

# JobDisabledError.__init__
"""Initialize with the ID of the disabled job."""
```

- [ ] **Step 8: Remove application/domain/ and application/__init__.py from per-file-ignores**

In `ruff.toml`, remove:
```toml
"src/table-maintenance/backend/application/domain/model/*" = ["D"]
"src/table-maintenance/backend/application/domain/__init__.py" = ["D"]
"src/table-maintenance/backend/application/exceptions.py" = ["D"]
"src/table-maintenance/backend/application/__init__.py" = ["D"]
```

Note: Keep `application/domain/service/*` suppressed — that's Task 5.

- [ ] **Step 9: Verify ruff passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check application/domain/model/ application/exceptions.py application/__init__.py`
Expected: No errors

- [ ] **Step 10: Verify tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/ tests/application/test_exceptions.py -q`
Expected: All pass

- [ ] **Step 11: Commit**

```bash
git add application/ ruff.toml
git commit -m "docs(domain): add docstrings to domain model layer"
```

---

### Task 4: Add docstrings to `application/port/` layer

**Files (~48 violations):**
- Modify: `application/port/__init__.py`
- Modify: `application/port/inbound/__init__.py`
- Modify: `application/port/inbound/job/__init__.py`
- Modify: `application/port/inbound/job/create_job/__init__.py`
- Modify: `application/port/inbound/job/create_job/input.py`
- Modify: `application/port/inbound/job/create_job/output.py`
- Modify: `application/port/inbound/job/create_job/use_case.py`
- Modify: `application/port/inbound/job/delete_job/__init__.py`
- Modify: `application/port/inbound/job/delete_job/input.py`
- Modify: `application/port/inbound/job/delete_job/output.py`
- Modify: `application/port/inbound/job/delete_job/use_case.py`
- Modify: `application/port/inbound/job/get_job/__init__.py`
- Modify: `application/port/inbound/job/get_job/input.py`
- Modify: `application/port/inbound/job/get_job/output.py`
- Modify: `application/port/inbound/job/get_job/use_case.py`
- Modify: `application/port/inbound/job/list_jobs/__init__.py`
- Modify: `application/port/inbound/job/list_jobs/input.py`
- Modify: `application/port/inbound/job/list_jobs/output.py`
- Modify: `application/port/inbound/job/list_jobs/use_case.py`
- Modify: `application/port/inbound/job/update_job/__init__.py`
- Modify: `application/port/inbound/job/update_job/input.py`
- Modify: `application/port/inbound/job/update_job/output.py`
- Modify: `application/port/inbound/job/update_job/use_case.py`
- Modify: `application/port/inbound/job_run/__init__.py`
- Modify: `application/port/inbound/job_run/create_job_run/__init__.py`
- Modify: `application/port/inbound/job_run/create_job_run/input.py`
- Modify: `application/port/inbound/job_run/create_job_run/output.py`
- Modify: `application/port/inbound/job_run/create_job_run/use_case.py`
- Modify: `application/port/inbound/job_run/get_job_run/__init__.py`
- Modify: `application/port/inbound/job_run/get_job_run/input.py`
- Modify: `application/port/inbound/job_run/get_job_run/output.py`
- Modify: `application/port/inbound/job_run/get_job_run/use_case.py`
- Modify: `application/port/inbound/job_run/list_job_runs/__init__.py`
- Modify: `application/port/inbound/job_run/list_job_runs/input.py`
- Modify: `application/port/inbound/job_run/list_job_runs/output.py`
- Modify: `application/port/inbound/job_run/list_job_runs/use_case.py`
- Modify: `application/port/outbound/__init__.py`
- Modify: `application/port/outbound/job/__init__.py`
- Modify: `application/port/outbound/job/jobs_repo.py`
- Modify: `application/port/outbound/job_run/__init__.py`
- Modify: `application/port/outbound/job_run/job_run_executor.py`
- Modify: `application/port/outbound/job_run/job_runs_repo.py`

- [ ] **Step 1: Add package docstrings (D104)**

```python
# application/port/__init__.py
"""Inbound and outbound port definitions."""

# application/port/inbound/__init__.py
"""Inbound port interfaces (use cases)."""

# application/port/inbound/job/__init__.py
"""Job use case interfaces and DTOs."""

# application/port/inbound/job/create_job/__init__.py
"""CreateJob use case definition."""

# application/port/inbound/job/delete_job/__init__.py
"""DeleteJob use case definition."""

# application/port/inbound/job/get_job/__init__.py
"""GetJob use case definition."""

# application/port/inbound/job/list_jobs/__init__.py
"""ListJobs use case definition."""

# application/port/inbound/job/update_job/__init__.py
"""UpdateJob use case definition."""

# application/port/inbound/job_run/__init__.py
"""JobRun use case interfaces and DTOs."""

# application/port/inbound/job_run/create_job_run/__init__.py
"""CreateJobRun use case definition."""

# application/port/inbound/job_run/get_job_run/__init__.py
"""GetJobRun use case definition."""

# application/port/inbound/job_run/list_job_runs/__init__.py
"""ListJobRuns use case definition."""

# application/port/outbound/__init__.py
"""Outbound port interfaces (repositories, executors)."""

# application/port/outbound/job/__init__.py
"""Job repository port."""

# application/port/outbound/job_run/__init__.py
"""JobRun repository and executor ports."""
```

- [ ] **Step 2: Add module docstrings (D100) to inbound port files**

Each `input.py`: `"""Define the <UseCaseName>Input dataclass."""`
Each `output.py`: `"""Define the <UseCaseName>Output dataclass."""`
Each `use_case.py`: `"""Define the <UseCaseName>UseCase interface."""`

Full list:
```python
# create_job/input.py
"""Define the CreateJobInput dataclass."""
# create_job/output.py
"""Define the CreateJobOutput dataclass."""
# create_job/use_case.py
"""Define the CreateJobUseCase interface."""

# delete_job/input.py
"""Define the DeleteJobInput dataclass."""
# delete_job/output.py
"""Define the DeleteJobOutput dataclass."""
# delete_job/use_case.py
"""Define the DeleteJobUseCase interface."""

# get_job/input.py
"""Define the GetJobInput dataclass."""
# get_job/output.py
"""Define the GetJobOutput dataclass."""
# get_job/use_case.py
"""Define the GetJobUseCase interface."""

# list_jobs/input.py
"""Define the ListJobsInput dataclass."""
# list_jobs/output.py
"""Define the ListJobsOutput dataclass."""
# list_jobs/use_case.py
"""Define the ListJobsUseCase interface."""

# update_job/input.py
"""Define the UpdateJobInput dataclass."""
# update_job/output.py
"""Define the UpdateJobOutput dataclass."""
# update_job/use_case.py
"""Define the UpdateJobUseCase interface."""

# create_job_run/input.py
"""Define the CreateJobRunInput dataclass."""
# create_job_run/output.py
"""Define the CreateJobRunOutput dataclass."""
# create_job_run/use_case.py
"""Define the CreateJobRunUseCase interface."""

# get_job_run/input.py
"""Define the GetJobRunInput dataclass."""
# get_job_run/output.py
"""Define the GetJobRunOutput dataclass."""
# get_job_run/use_case.py
"""Define the GetJobRunUseCase interface."""

# list_job_runs/input.py
"""Define the ListJobRunsInput dataclass."""
# list_job_runs/output.py
"""Define the ListJobRunsOutput dataclass."""
# list_job_runs/use_case.py
"""Define the ListJobRunsUseCase interface."""
```

- [ ] **Step 3: Add module docstrings (D100) to outbound port files**

```python
# application/port/outbound/job/jobs_repo.py
"""Define the JobsRepo port interface."""

# application/port/outbound/job_run/job_run_executor.py
"""Define the JobRunExecutor port interface."""

# application/port/outbound/job_run/job_runs_repo.py
"""Define the JobRunsRepo port interface."""
```

- [ ] **Step 4: Add method docstrings to JobsRepo**

In `application/port/outbound/job/jobs_repo.py`:
```python
@abstractmethod
def update(self, entity: Job) -> Job:
    """Persist changes to an existing job and return the updated entity."""
    ...
```

- [ ] **Step 5: Add method docstrings to JobRunsRepo**

In `application/port/outbound/job_run/job_runs_repo.py`:
```python
@abstractmethod
def create(self, entity: JobRun) -> JobRun:
    """Persist a new job run and return it."""
    ...

@abstractmethod
def get(self, run_id: JobRunId) -> JobRun:
    """Retrieve a job run by its identifier."""
    ...

@abstractmethod
def list_for_job(self, job_id: JobId) -> list[JobRun]:
    """Return all job runs for the given job."""
    ...

@abstractmethod
def list_all(self) -> list[JobRun]:
    """Return all job runs."""
    ...
```

- [ ] **Step 6: Add method docstring to JobRunExecutor**

In `application/port/outbound/job_run/job_run_executor.py`:
```python
@abstractmethod
def trigger(self, job: Job) -> JobRun:
    """Trigger execution of the given job and return the resulting run."""
    ...
```

- [ ] **Step 7: Remove application/port/ from per-file-ignores**

In `ruff.toml`, remove:
```toml
"src/table-maintenance/backend/application/port/*" = ["D"]
```

- [ ] **Step 8: Verify ruff passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check application/port/`
Expected: No errors

- [ ] **Step 9: Verify tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/ -q`
Expected: All pass

- [ ] **Step 10: Commit**

```bash
git add application/port/ ruff.toml
git commit -m "docs(port): add docstrings to inbound and outbound ports"
```

---

### Task 5: Add docstrings to `application/domain/service/` layer

**Files (~27 violations):**
- Modify: `application/domain/service/__init__.py`
- Modify: `application/domain/service/job/__init__.py`
- Modify: `application/domain/service/job/create_job.py`
- Modify: `application/domain/service/job/delete_job.py`
- Modify: `application/domain/service/job/get_job.py`
- Modify: `application/domain/service/job/list_jobs.py`
- Modify: `application/domain/service/job/update_job.py`
- Modify: `application/domain/service/job_run/__init__.py`
- Modify: `application/domain/service/job_run/create_job_run.py`
- Modify: `application/domain/service/job_run/get_job_run.py`
- Modify: `application/domain/service/job_run/list_job_runs.py`

- [ ] **Step 1: Add package docstrings (D104)**

```python
# application/domain/service/__init__.py
"""Use case service implementations."""

# application/domain/service/job/__init__.py
"""Job use case services."""

# application/domain/service/job_run/__init__.py
"""JobRun use case services."""
```

- [ ] **Step 2: Add module docstrings (D100)**

```python
# create_job.py
"""Define the CreateJobService."""

# delete_job.py
"""Define the DeleteJobService."""

# get_job.py
"""Define the GetJobService."""

# list_jobs.py
"""Define the ListJobsService."""

# update_job.py
"""Define the UpdateJobService."""

# create_job_run.py
"""Define the CreateJobRunService."""

# get_job_run.py
"""Define the GetJobRunService."""

# list_job_runs.py
"""Define the ListJobRunsService."""
```

- [ ] **Step 3: Add __init__ and execute docstrings to job services**

Each service class gets an `__init__` and `execute` docstring. Pattern:

```python
# CreateJobService
def __init__(self, repo: JobsRepo) -> None:
    """Initialize with the jobs repository."""

def execute(self, request: CreateJobInput) -> CreateJobOutput:
    """Create a new job from the given input and persist it."""

# DeleteJobService
def __init__(self, repo: JobsRepo) -> None:
    """Initialize with the jobs repository."""

def execute(self, request: DeleteJobInput) -> DeleteJobOutput:
    """Delete the job identified by the input."""

# GetJobService
def __init__(self, repo: JobsRepo) -> None:
    """Initialize with the jobs repository."""

def execute(self, request: GetJobInput) -> GetJobOutput:
    """Retrieve a job by its identifier."""

# ListJobsService
def __init__(self, repo: JobsRepo) -> None:
    """Initialize with the jobs repository."""

def execute(self, request: ListJobsInput) -> ListJobsOutput:
    """Return all jobs."""

# UpdateJobService
def __init__(self, repo: JobsRepo) -> None:
    """Initialize with the jobs repository."""

def execute(self, request: UpdateJobInput) -> UpdateJobOutput:
    """Apply partial updates to the specified job."""
```

- [ ] **Step 4: Add __init__ and execute docstrings to job_run services**

```python
# CreateJobRunService
def __init__(self, repo: JobsRepo, executor: JobRunExecutor) -> None:
    """Initialize with the jobs repository and job run executor."""

def execute(self, request: CreateJobRunInput) -> CreateJobRunOutput:
    """Trigger a new execution of the specified job."""

# GetJobRunService
def __init__(self, repo: JobRunsRepo) -> None:
    """Initialize with the job runs repository."""

def execute(self, request: GetJobRunInput) -> GetJobRunOutput:
    """Retrieve a job run by its identifier."""

# ListJobRunsService
def __init__(self, repo: JobRunsRepo) -> None:
    """Initialize with the job runs repository."""

def execute(self, request: ListJobRunsInput) -> ListJobRunsOutput:
    """Return all job runs for the specified job."""
```

- [ ] **Step 5: Remove application/domain/service/ from per-file-ignores**

In `ruff.toml`, remove:
```toml
"src/table-maintenance/backend/application/domain/service/*" = ["D"]
```

- [ ] **Step 6: Verify ruff passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check application/domain/service/`
Expected: No errors

- [ ] **Step 7: Verify tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/service/ -q`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add application/domain/service/ ruff.toml
git commit -m "docs(service): add docstrings to use case services"
```

---

### Task 6: Add docstrings to `adapter/outbound/` layer

**Files (~62 violations):**
- Modify: `adapter/outbound/__init__.py`
- Modify: `adapter/outbound/job/__init__.py`
- Modify: `adapter/outbound/job/jobs_in_memory_repo.py`
- Modify: `adapter/outbound/job/sql/__init__.py`
- Modify: `adapter/outbound/job/sql/job_to_values.py`
- Modify: `adapter/outbound/job/sql/jobs_sql_repo.py`
- Modify: `adapter/outbound/job/sql/jobs_table.py`
- Modify: `adapter/outbound/job/sql/row_to_job.py`
- Modify: `adapter/outbound/job_run/__init__.py`
- Modify: `adapter/outbound/job_run/job_run_in_memory_executor.py`
- Modify: `adapter/outbound/job_run/job_runs_in_memory_repo.py`
- Modify: `adapter/outbound/job_run/k8s/__init__.py`
- Modify: `adapter/outbound/job_run/k8s/job_run_k8s_executor.py`
- Modify: `adapter/outbound/job_run/k8s/job_runs_k8s_repo.py`
- Modify: `adapter/outbound/job_run/k8s/manifest.py`
- Modify: `adapter/outbound/job_run/k8s/status_mapper.py`
- Modify: `adapter/outbound/job_run/sql/__init__.py`
- Modify: `adapter/outbound/job_run/sql/job_run_to_values.py`
- Modify: `adapter/outbound/job_run/sql/job_runs_sql_repo.py`
- Modify: `adapter/outbound/job_run/sql/job_runs_table.py`
- Modify: `adapter/outbound/job_run/sql/row_to_job_run.py`
- Modify: `adapter/outbound/sql/engine_factory.py`
- Modify: `adapter/outbound/sql/metadata.py`

- [ ] **Step 1: Add package docstrings (D104)**

```python
# adapter/outbound/__init__.py
"""Outbound adapter implementations."""

# adapter/outbound/job/__init__.py
"""Job repository adapters."""

# adapter/outbound/job/sql/__init__.py
"""SQL-backed Job repository components."""

# adapter/outbound/job_run/__init__.py
"""JobRun repository and executor adapters."""

# adapter/outbound/job_run/k8s/__init__.py
"""Kubernetes-backed JobRun adapters."""

# adapter/outbound/job_run/sql/__init__.py
"""SQL-backed JobRun repository components."""
```

- [ ] **Step 2: Add module docstrings (D100) to all outbound adapter files**

```python
# jobs_in_memory_repo.py
"""Define the JobsInMemoryRepo adapter."""

# job_to_values.py
"""Provide the job_to_values serializer."""

# jobs_sql_repo.py
"""Define the JobsSqlRepo adapter."""

# jobs_table.py
"""Define the jobs SQLAlchemy table schema."""

# row_to_job.py
"""Provide the row_to_job deserializer."""

# job_run_in_memory_executor.py
"""Define the JobRunInMemoryExecutor adapter."""

# job_runs_in_memory_repo.py
"""Define the JobRunsInMemoryRepo adapter."""

# job_run_k8s_executor.py
"""Define the JobRunK8sExecutor adapter."""

# job_runs_k8s_repo.py
"""Define the JobRunsK8sRepo adapter."""

# manifest.py
"""Provide the build_manifest helper for Kubernetes job manifests."""

# status_mapper.py
"""Provide the status_from_k8s mapping function."""

# job_run_to_values.py
"""Provide the job_run_to_values serializer."""

# job_runs_sql_repo.py
"""Define the JobRunsSqlRepo adapter."""

# job_runs_table.py
"""Define the job_runs SQLAlchemy table schema."""

# row_to_job_run.py
"""Provide the row_to_job_run deserializer."""

# engine_factory.py
"""Provide the build_engine factory function."""

# metadata.py
"""Provide the shared SQLAlchemy MetaData instance."""
```

- [ ] **Step 3: Add class docstrings where missing**

```python
# JobsInMemoryRepo
"""In-memory implementation of JobsRepo for testing."""

# JobRunsInMemoryRepo
"""In-memory implementation of JobRunsRepo for testing."""
```

- [ ] **Step 4: Add method docstrings to JobsInMemoryRepo**

```python
def __init__(self) -> None:
    """Initialize with an empty job store."""

def create(self, entity: Job) -> Job:
    """Store a new job in memory and return it."""

def get(self, entity_id: EntityId) -> Job:
    """Retrieve a job by its identifier."""

def list_all(self) -> list[Job]:
    """Return all stored jobs."""

def delete(self, entity_id: EntityId) -> None:
    """Remove a job by its identifier."""

def update(self, entity: Job) -> Job:
    """Replace a stored job and return it."""
```

- [ ] **Step 5: Add method docstrings to JobsSqlRepo**

```python
def __init__(self, engine: Engine) -> None:
    """Initialize with a SQLAlchemy engine."""

def create(self, entity: Job) -> Job:
    """Insert a new job row and return the entity."""

def get(self, entity_id: EntityId) -> Job:
    """Retrieve a job row by its identifier."""

def list_all(self) -> list[Job]:
    """Return all job rows."""

def delete(self, entity_id: EntityId) -> None:
    """Delete a job row by its identifier."""

def update(self, entity: Job) -> Job:
    """Update an existing job row and return the entity."""
```

- [ ] **Step 6: Add function docstrings to serializers/deserializers**

```python
# job_to_values
def job_to_values(job: Job) -> dict:
    """Convert a Job domain entity to a dict of SQL column values."""

# row_to_job
def row_to_job(row: Any) -> Job:
    """Convert a SQL row to a Job domain entity."""

# job_run_to_values
def job_run_to_values(run: JobRun) -> dict:
    """Convert a JobRun domain entity to a dict of SQL column values."""

# row_to_job_run
def row_to_job_run(row: Any) -> JobRun:
    """Convert a SQL row to a JobRun domain entity."""

# status_from_k8s
def status_from_k8s(kind: str, state: str) -> JobRunStatus:
    """Map a Kubernetes SparkApplication state to a JobRunStatus."""

# build_engine
def build_engine(backend: DatabaseBackend, settings: AppSettings) -> Engine:
    """Create a SQLAlchemy engine from the given backend and settings."""
```

- [ ] **Step 7: Add method docstrings to JobRunsInMemoryRepo**

```python
def __init__(self) -> None:
    """Initialize with an empty job run store."""

def create(self, entity: JobRun) -> JobRun:
    """Store a new job run in memory and return it."""

def get(self, run_id: JobRunId) -> JobRun:
    """Retrieve a job run by its identifier."""

def list_for_job(self, job_id: JobId) -> list[JobRun]:
    """Return all job runs for the given job."""

def list_all(self) -> list[JobRun]:
    """Return all stored job runs."""
```

- [ ] **Step 8: Add method docstrings to JobRunInMemoryExecutor**

```python
def __init__(self) -> None:
    """Initialize with an empty triggered runs list."""

def trigger(self, job: Job) -> JobRun:
    """Record and return a new pending job run for the given job."""
```

- [ ] **Step 9: Add method docstrings to K8s adapters**

```python
# JobRunK8sExecutor
def __init__(self, api: CustomObjectsApi, settings: AppSettings) -> None:
    """Initialize with the Kubernetes API client and app settings."""

def trigger(self, job: Job) -> JobRun:
    """Create a SparkApplication CRD and return the resulting job run."""

# JobRunsK8sRepo
def __init__(self, api: CustomObjectsApi, settings: AppSettings) -> None:
    """Initialize with the Kubernetes API client and app settings."""

def create(self, entity: JobRun) -> JobRun:
    """Raise NotImplementedError; K8s repo is read-only."""

def get(self, run_id: JobRunId) -> JobRun:
    """Retrieve a job run from Kubernetes by its resource name."""

def list_for_job(self, job_id: JobId) -> list[JobRun]:
    """Return all SparkApplication runs for the given job."""

def list_all(self) -> list[JobRun]:
    """Return all SparkApplication and ScheduledSparkApplication runs."""
```

- [ ] **Step 10: Add method docstrings to JobRunsSqlRepo**

```python
def __init__(self, engine: Engine) -> None:
    """Initialize with a SQLAlchemy engine."""

def create(self, entity: JobRun) -> JobRun:
    """Insert a new job run row and return the entity."""

def get(self, run_id: JobRunId) -> JobRun:
    """Retrieve a job run row by its identifier."""

def list_for_job(self, job_id: JobId) -> list[JobRun]:
    """Return all job run rows for the given job."""

def list_all(self) -> list[JobRun]:
    """Return all job run rows."""
```

- [ ] **Step 11: Remove adapter/outbound/ from per-file-ignores**

In `ruff.toml`, remove:
```toml
"src/table-maintenance/backend/adapter/outbound/*" = ["D"]
```

- [ ] **Step 12: Verify ruff passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check adapter/outbound/`
Expected: No errors

- [ ] **Step 13: Verify tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/ -q`
Expected: All pass

- [ ] **Step 14: Commit**

```bash
git add adapter/outbound/ ruff.toml
git commit -m "docs(adapter): add docstrings to outbound adapters"
```

---

### Task 7: Add docstrings to `adapter/inbound/` layer

**Files (~25 violations):**
- Modify: `adapter/__init__.py`
- Modify: `adapter/inbound/__init__.py`
- Modify: `adapter/inbound/web/__init__.py`
- Modify: `adapter/inbound/web/job/__init__.py`
- Modify: `adapter/inbound/web/job/create_job.py`
- Modify: `adapter/inbound/web/job/delete_job.py`
- Modify: `adapter/inbound/web/job/get_job.py`
- Modify: `adapter/inbound/web/job/list_jobs.py`
- Modify: `adapter/inbound/web/job/update_job.py`
- Modify: `adapter/inbound/web/job/dto.py`
- Modify: `adapter/inbound/web/job_run/__init__.py`
- Modify: `adapter/inbound/web/job_run/create_job_run.py`
- Modify: `adapter/inbound/web/job_run/get_job_run.py`
- Modify: `adapter/inbound/web/job_run/list_job_runs.py`
- Modify: `adapter/inbound/web/job_run/dto.py`

- [ ] **Step 1: Add package docstrings (D104)**

```python
# adapter/__init__.py
"""Inbound and outbound adapters."""

# adapter/inbound/__init__.py
"""Inbound adapters (web API)."""

# adapter/inbound/web/__init__.py
"""FastAPI web adapter."""

# adapter/inbound/web/job/__init__.py
"""Job REST API endpoints."""

# adapter/inbound/web/job_run/__init__.py
"""JobRun REST API endpoints."""
```

- [ ] **Step 2: Add module docstrings (D100) and function docstrings (D103)**

```python
# create_job.py
"""Define the POST /jobs endpoint."""
# function:
"""Create a new job from the request body."""

# delete_job.py
"""Define the DELETE /jobs/{name} endpoint."""
# function:
"""Delete a job by its name."""

# get_job.py
"""Define the GET /jobs/{name} endpoint."""
# function:
"""Retrieve a job by its name."""

# list_jobs.py
"""Define the GET /jobs endpoint."""
# function:
"""Return all jobs."""

# update_job.py
"""Define the PATCH /jobs/{name} endpoint."""
# function:
"""Apply partial updates to a job."""

# create_job_run.py
"""Define the POST /jobs/{name}/runs endpoint."""
# function:
"""Trigger a new run for the specified job."""

# get_job_run.py
"""Define the GET /runs/{run_id} endpoint."""
# function:
"""Retrieve a job run by its identifier."""

# list_job_runs.py
"""Define the GET /jobs/{name}/runs endpoint."""
# function:
"""Return all runs for the specified job."""
```

- [ ] **Step 3: Add module and class docstrings to DTOs**

```python
# adapter/inbound/web/job/dto.py
"""Define Job API request and response DTOs."""

# JobApiRequest
"""Request body for creating a new job."""

# JobApiResponse (or UpdateJobApiRequest and JobApiResponse — check exact class names)
"""Response body for job endpoints."""

# adapter/inbound/web/job_run/dto.py
"""Define JobRun API response DTO."""

# JobRunApiResponse
"""Response body for job run endpoints."""
```

- [ ] **Step 4: Remove adapter/inbound/ and adapter/__init__.py from per-file-ignores**

In `ruff.toml`, remove:
```toml
"src/table-maintenance/backend/adapter/inbound/*" = ["D"]
"src/table-maintenance/backend/adapter/__init__.py" = ["D"]
```

- [ ] **Step 5: Verify ruff passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check adapter/`
Expected: No errors

- [ ] **Step 6: Verify tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/inbound/ -q`
Expected: All pass

- [ ] **Step 7: Commit**

```bash
git add adapter/ ruff.toml
git commit -m "docs(adapter): add docstrings to inbound web adapters"
```

---

### Task 8: Add docstrings to `configs/`, `dependencies/`, and `main.py`

**Files (~32 violations):**
- Modify: `configs/__init__.py`
- Modify: `configs/app.py`
- Modify: `configs/database_backend.py`
- Modify: `configs/job_run_executor_adapter.py`
- Modify: `configs/job_runs_repo_adapter.py`
- Modify: `configs/jobs_repo_adapter.py`
- Modify: `configs/k8s_settings.py`
- Modify: `configs/postgres_settings.py`
- Modify: `configs/sqlite_settings.py`
- Modify: `dependencies/__init__.py`
- Modify: `dependencies/k8s.py`
- Modify: `dependencies/repos.py`
- Modify: `dependencies/settings.py`
- Modify: `dependencies/use_cases.py`
- Modify: `main.py`

- [ ] **Step 1: Add package docstrings (D104)**

```python
# configs/__init__.py
"""Application configuration models and enumerations."""

# dependencies/__init__.py
"""FastAPI dependency injection providers."""
```

- [ ] **Step 2: Add module and class docstrings to configs/**

```python
# configs/app.py
"""Define the AppSettings configuration model."""
# AppSettings class:
"""Root application settings loaded from environment variables."""

# configs/database_backend.py
"""Define the DatabaseBackend enumeration."""
# DatabaseBackend class:
"""Enumerate supported database backends."""

# configs/job_run_executor_adapter.py
"""Define the JobRunExecutorAdapter enumeration."""
# JobRunExecutorAdapter class:
"""Enumerate supported JobRunExecutor implementations."""

# configs/job_runs_repo_adapter.py
"""Define the JobRunsRepoAdapter enumeration."""
# JobRunsRepoAdapter class:
"""Enumerate supported JobRunsRepo implementations."""

# configs/jobs_repo_adapter.py
"""Define the JobsRepoAdapter enumeration."""
# JobsRepoAdapter class:
"""Enumerate supported JobsRepo implementations."""

# configs/k8s_settings.py
"""Define the K8sSettings configuration model."""
# K8sSettings class:
"""Kubernetes and Spark driver/executor configuration."""

# configs/postgres_settings.py
"""Define the PostgresSettings configuration model."""
# PostgresSettings class:
"""PostgreSQL connection and pool configuration."""

# configs/sqlite_settings.py
"""Define the SqliteSettings configuration model."""
# SqliteSettings class:
"""SQLite database path configuration."""
```

- [ ] **Step 3: Add module and function docstrings to dependencies/**

```python
# dependencies/k8s.py
"""Provide the Kubernetes API client dependency."""
# get_k8s_api function:
"""Return a cached Kubernetes CustomObjectsApi client."""

# dependencies/repos.py
"""Provide repository and executor dependencies."""

# dependencies/settings.py
"""Provide the application settings dependency."""
# get_settings function:
"""Return a cached AppSettings instance."""

# dependencies/use_cases.py
"""Provide use case dependencies."""
```

For each use case factory in `dependencies/use_cases.py`:
```python
def get_create_job_use_case(...) -> CreateJobUseCase:
    """Provide the CreateJob use case with injected dependencies."""

def get_delete_job_use_case(...) -> DeleteJobUseCase:
    """Provide the DeleteJob use case with injected dependencies."""

def get_get_job_use_case(...) -> GetJobUseCase:
    """Provide the GetJob use case with injected dependencies."""

def get_list_jobs_use_case(...) -> ListJobsUseCase:
    """Provide the ListJobs use case with injected dependencies."""

def get_update_job_use_case(...) -> UpdateJobUseCase:
    """Provide the UpdateJob use case with injected dependencies."""

def get_create_job_run_use_case(...) -> CreateJobRunUseCase:
    """Provide the CreateJobRun use case with injected dependencies."""

def get_list_job_runs_use_case(...) -> ListJobRunsUseCase:
    """Provide the ListJobRuns use case with injected dependencies."""

def get_get_job_run_use_case(...) -> GetJobRunUseCase:
    """Provide the GetJobRun use case with injected dependencies."""
```

- [ ] **Step 4: Add module and function docstrings to main.py**

```python
# main.py
"""FastAPI application entry point for the table-maintenance backend."""

# lifespan function:
"""Initialize SQL tables on startup when SQL repositories are configured."""

# health function:
"""Return a health check response."""
```

- [ ] **Step 5: Remove configs/, dependencies/, and main.py from per-file-ignores**

In `ruff.toml`, remove:
```toml
"src/table-maintenance/backend/configs/*" = ["D"]
"src/table-maintenance/backend/dependencies/*" = ["D"]
"src/table-maintenance/backend/main.py" = ["D"]
```

- [ ] **Step 6: Verify ruff passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check configs/ dependencies/ main.py`
Expected: No errors

- [ ] **Step 7: Verify tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/configs/ tests/dependencies/ -q`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add configs/ dependencies/ main.py ruff.toml
git commit -m "docs(infra): add docstrings to configs, dependencies, and main"
```

---

### Task 9: Add docstrings to `tests/` layer

**Files (~362 violations — largest task):**

This is the largest task. All test files need module docstrings (D100), package docstrings (D104), and function docstrings (D103). Test helper classes in `tests/base/` also need class docstrings (D101).

The general patterns:

- **Module docstrings**: `"""Tests for <ModuleName>."""`
- **Package `__init__.py`**: `"""Tests for the <layer> package."""`
- **Test functions**: One-line summary describing the assertion in imperative mood: `"""Return empty list when no jobs exist."""`
- **Fixtures in conftest.py**: `"""Provide <what the fixture returns>."""`
- **Test helper classes** (stubs/fakes in test files): `"""Test stub for <what it stubs>."""`

- [ ] **Step 1: Add package docstrings to all test `__init__.py` files**

Add `"""Tests for <package>."""` to each:

```python
# tests/__init__.py
"""Test suite for the table-maintenance backend."""

# tests/adapter/__init__.py
"""Tests for adapter layer."""

# tests/adapter/inbound/__init__.py
"""Tests for inbound adapters."""

# tests/adapter/inbound/web/__init__.py
"""Tests for web adapter endpoints."""

# tests/adapter/inbound/web/job/__init__.py
"""Tests for job API endpoints."""

# tests/adapter/inbound/web/job_run/__init__.py
"""Tests for job run API endpoints."""

# tests/adapter/outbound/__init__.py
"""Tests for outbound adapters."""

# tests/adapter/outbound/job/__init__.py
"""Tests for job repository adapters."""

# tests/adapter/outbound/job/sql/__init__.py
"""Tests for SQL job repository."""

# tests/adapter/outbound/job_run/__init__.py
"""Tests for job run adapters."""

# tests/adapter/outbound/job_run/k8s/__init__.py
"""Tests for Kubernetes job run adapters."""

# tests/adapter/outbound/job_run/sql/__init__.py
"""Tests for SQL job run repository."""

# tests/adapter/outbound/sql/__init__.py
"""Tests for shared SQL infrastructure."""

# tests/application/__init__.py
"""Tests for application layer."""

# tests/application/domain/__init__.py
"""Tests for domain model."""

# tests/application/domain/model/__init__.py
"""Tests for domain entities and value objects."""

# tests/application/domain/model/job/__init__.py
"""Tests for Job aggregate."""

# tests/application/domain/model/job_run/__init__.py
"""Tests for JobRun aggregate."""

# tests/application/domain/service/__init__.py
"""Tests for use case services."""

# tests/application/domain/service/job/__init__.py
"""Tests for job services."""

# tests/application/domain/service/job_run/__init__.py
"""Tests for job run services."""

# tests/application/port/__init__.py
"""Tests for port interfaces."""

# tests/application/port/outbound/__init__.py
"""Tests for outbound ports."""

# tests/application/port/outbound/job/__init__.py
"""Tests for job outbound ports."""

# tests/application/port/outbound/job_run/__init__.py
"""Tests for job run outbound ports."""

# tests/architecture/__init__.py
"""Architecture contract tests."""

# tests/base/__init__.py
"""Tests for base shared kernel."""

# tests/configs/__init__.py
"""Tests for configuration models."""

# tests/dependencies/__init__.py
"""Tests for dependency injection providers."""
```

- [ ] **Step 2: Add module docstrings and function docstrings to test files**

For each test file, add a module docstring and a one-line docstring to every test function and fixture. The docstring should describe what the test verifies.

Read each test file, understand what each test function asserts, and add an appropriate one-line docstring. The pattern is always:

```python
def test_something(self_or_fixture):
    """Verify that <expected behavior> when <condition>."""
```

For fixtures:
```python
def some_fixture():
    """Provide <what it returns>."""
```

**Important:** Since there are ~260 test function violations across ~45 test files, the implementer must read each test function to write an accurate docstring. Do not write generic docstrings — each must reflect the actual assertion.

The test files to process (grouped by package):

**tests/base/** (7 files):
- `test_value_object.py`, `test_entity_id.py`, `test_entity.py`, `test_aggregate_root.py`, `test_domain_event.py`, `test_repository.py`, `test_use_case.py`

**tests/application/domain/model/job/** (4 files):
- `test_job.py`, `test_job_id.py`, `test_job_request.py`, `test_exceptions.py`

**tests/application/domain/model/job_run/** (4 files):
- `test_job_run.py`, `test_job_run_id.py`, `test_job_run_status.py`, `test_exceptions.py`

**tests/application/domain/service/job/** (5 files):
- `test_create_job.py`, `test_delete_job.py`, `test_get_job.py`, `test_list_jobs.py`, `test_update_job.py`

**tests/application/domain/service/job_run/** (3 files):
- `test_create_job_run.py`, `test_get_job_run.py`, `test_list_job_runs.py`

**tests/application/port/outbound/job/** (1 file):
- `test_jobs_repo.py`

**tests/application/port/outbound/job_run/** (2 files):
- `test_job_run_executor.py`, `test_job_runs_repo.py`

**tests/application/** (1 file):
- `test_exceptions.py`

**tests/adapter/inbound/web/job/** (5 files):
- `test_create_job.py`, `test_delete_job.py`, `test_get_job.py`, `test_list_jobs.py`, `test_update_job.py`

**tests/adapter/inbound/web/job_run/** (3 files):
- `test_create_job_run.py`, `test_get_job_run.py`, `test_list_job_runs.py`

**tests/adapter/inbound/web/** (1 file):
- `test_health.py`

**tests/adapter/outbound/job/sql/** (5 files + conftest):
- `conftest.py`, `test_job_to_values.py`, `test_jobs_table.py`, `test_row_to_job.py`, `test_sql_jobs_repo.py`

**tests/adapter/outbound/job/** (1 file):
- `test_in_memory_jobs_repo.py`

**tests/adapter/outbound/job_run/sql/** (4 files + conftest):
- `conftest.py`, `test_job_run_to_values.py`, `test_job_runs_table.py`, `test_row_to_job_run.py`, `test_sql_job_runs_repo.py`

**tests/adapter/outbound/job_run/k8s/** (4 files):
- `test_k8s_job_run_executor.py`, `test_k8s_job_runs_repo.py`, `test_manifest.py`, `test_status_mapper.py`

**tests/adapter/outbound/job_run/** (2 files):
- `test_in_memory_job_run_executor.py`, `test_in_memory_job_runs_repo.py`

**tests/adapter/outbound/sql/** (1 file + conftest):
- `conftest.py`, `test_engine_factory.py`

**tests/configs/** (8 files):
- `test_app.py`, `test_database_backend.py`, `test_job_run_executor_adapter.py`, `test_job_runs_repo_adapter.py`, `test_jobs_repo_adapter.py`, `test_k8s_settings.py`, `test_postgres_settings.py`, `test_sqlite_settings.py`, `test_adapter_settings.py`

**tests/dependencies/** (4 files + conftest):
- `conftest.py`, `test_k8s.py`, `test_repos.py`, `test_settings.py`, `test_use_cases.py`

**tests/architecture/** (1 file):
- `test_inbound_port_structure.py`

**tests/** (2 files):
- `conftest.py`, `test_integration.py`

- [ ] **Step 3: Add class docstrings to test helper classes**

In `tests/base/` files, test helper classes (stubs like `ConcreteValueObject`, `ConcreteEntityId`, `ConcreteEntity`, `ConcreteAggregateRoot`, `SampleEvent`, `ConcreteRepo`) need class docstrings:

```python
class ConcreteValueObject(ValueObject):
    """Test stub for ValueObject."""

class ConcreteEntityId(EntityId):
    """Test stub for EntityId."""

# etc. — read each file and add appropriate docstring
```

- [ ] **Step 4: Remove tests/ from per-file-ignores**

In `ruff.toml`, remove:
```toml
"src/table-maintenance/backend/tests/*" = ["D"]
```

- [ ] **Step 5: Verify ruff passes for all tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check tests/`
Expected: No errors

- [ ] **Step 6: Verify all tests pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -q`
Expected: 304 passed

- [ ] **Step 7: Commit**

```bash
git add tests/ ruff.toml
git commit -m "docs(tests): add docstrings to all test files"
```

---

### Task 10: Final cleanup and verification

- [ ] **Step 1: Verify no remaining per-file-ignores for D rules**

Check that `ruff.toml` `[lint.per-file-ignores]` only contains:
```toml
[lint.per-file-ignores]
"tests/*" = ["FA100"]
```

- [ ] **Step 2: Run full ruff check**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check .`
Expected: No errors

- [ ] **Step 3: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: 304 passed

- [ ] **Step 4: Run lint-imports**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`
Expected: All contracts satisfied

- [ ] **Step 5: Commit if any cleanup was needed**

Only commit if changes were made in this task. If everything was clean from prior tasks, skip.

```bash
git commit -m "docs(lint): remove pydocstyle per-file-ignores after full coverage"
```
