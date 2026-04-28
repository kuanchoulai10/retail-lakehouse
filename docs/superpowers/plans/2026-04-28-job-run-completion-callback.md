# Job Run Completion Callback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable runtimes (Spark, future Trino) to report job run results back to the backend via REST API callback, so the frontend can display completion status and metadata.

**Architecture:** Two new use cases (CompleteJobRun, FailJobRun) receive callback HTTP requests and transition the JobRun aggregate through its state machine. The domain model is extended with a `JobRunResult` value object. A `save` method is added to `JobRunsRepo` for updating existing runs. The SubmitJobRunService is modified to mark runs as RUNNING after successful submission.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, dataclasses, pytest

**Spec:** `docs/superpowers/specs/2026-04-28-job-run-completion-callback-design.md`

**Run tests:** `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

**Run single test:** `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/<path>::<test_name> -v`

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `application/domain/model/job_run/job_run_result.py` | `JobRunResult` value object |
| `application/port/inbound/job_run/complete_job_run/use_case.py` | `CompleteJobRunUseCase` interface |
| `application/port/inbound/job_run/complete_job_run/input.py` | `CompleteJobRunInput` |
| `application/port/inbound/job_run/complete_job_run/output.py` | `CompleteJobRunOutput` |
| `application/port/inbound/job_run/complete_job_run/__init__.py` | Re-exports |
| `application/port/inbound/job_run/fail_job_run/use_case.py` | `FailJobRunUseCase` interface |
| `application/port/inbound/job_run/fail_job_run/input.py` | `FailJobRunInput` |
| `application/port/inbound/job_run/fail_job_run/output.py` | `FailJobRunOutput` |
| `application/port/inbound/job_run/fail_job_run/__init__.py` | Re-exports |
| `application/service/job_run/complete_job_run.py` | `CompleteJobRunService` |
| `application/service/job_run/fail_job_run.py` | `FailJobRunService` |
| `adapter/inbound/web/job_run/complete_job_run.py` | POST /runs/{run_id}/complete endpoint |
| `adapter/inbound/web/job_run/fail_job_run.py` | POST /runs/{run_id}/fail endpoint |
| `tests/application/domain/model/job_run/test_job_run_result.py` | Tests for JobRunResult |
| `tests/application/service/job_run/test_complete_job_run.py` | Tests for CompleteJobRunService |
| `tests/application/service/job_run/test_fail_job_run.py` | Tests for FailJobRunService |

### Modified files

| File | Change |
|------|--------|
| `application/domain/model/job_run/job_run.py` | Add `result` field, modify `mark_completed`/`mark_failed` signatures |
| `application/domain/model/job_run/events.py` | Add `result`/`error` fields to events |
| `application/domain/model/job_run/__init__.py` | Re-export `JobRunResult` |
| `application/port/outbound/job_run/job_runs_repo.py` | Add `save()` abstract method |
| `adapter/outbound/job_run/job_runs_in_memory_repo.py` | Implement `save()` |
| `adapter/outbound/job_run/sql/job_runs_sql_repo.py` | Implement `save()` |
| `adapter/outbound/job_run/sql/job_runs_table.py` | Add `error`, `result_duration_ms`, `result_metadata` columns |
| `adapter/outbound/job_run/sql/job_run_to_values.py` | Serialize new fields |
| `adapter/outbound/job_run/sql/row_to_job_run.py` | Deserialize new fields |
| `application/port/inbound/job_run/__init__.py` | Re-export new use case types |
| `application/port/inbound/__init__.py` | Re-export new use case types |
| `adapter/inbound/web/job_run/__init__.py` | Include new routers |
| `adapter/inbound/web/job_run/dto.py` | Add result fields to response DTO |
| `bootstrap/dependencies/use_cases.py` | Add DI for new use cases |
| `application/service/job_run/get_job_run.py` | Return result fields in output |
| `application/port/inbound/job_run/get_job_run/output.py` | Add result fields |
| `application/service/job_run/submit_job_run.py` | Mark run as RUNNING after submit |

All paths below are relative to `src/table-maintenance/backend/`.

---

## Task 1: JobRunResult Value Object

**Files:**
- Create: `application/domain/model/job_run/job_run_result.py`
- Create: `tests/application/domain/model/job_run/test_job_run_result.py`
- Modify: `application/domain/model/job_run/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/application/domain/model/job_run/test_job_run_result.py`:

```python
"""Tests for JobRunResult."""

from __future__ import annotations

from base import ValueObject
from application.domain.model.job_run.job_run_result import JobRunResult


def test_is_value_object():
    """Verify that JobRunResult is a ValueObject."""
    assert issubclass(JobRunResult, ValueObject)


def test_fields():
    """Verify that all fields are stored correctly."""
    result = JobRunResult(
        duration_ms=1500,
        metadata={"expired_snapshots": "42"},
    )
    assert result.duration_ms == 1500
    assert result.metadata == {"expired_snapshots": "42"}


def test_none_duration():
    """Verify that duration_ms can be None."""
    result = JobRunResult(duration_ms=None, metadata={})
    assert result.duration_ms is None


def test_equality_by_value():
    """Verify that two results with same values are equal."""
    a = JobRunResult(duration_ms=100, metadata={"k": "v"})
    b = JobRunResult(duration_ms=100, metadata={"k": "v"})
    assert a == b


def test_immutable():
    """Verify that JobRunResult is frozen."""
    result = JobRunResult(duration_ms=100, metadata={})
    try:
        result.duration_ms = 200  # type: ignore[misc]
        assert False, "Should have raised"
    except AttributeError:
        pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job_run/test_job_run_result.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'application.domain.model.job_run.job_run_result'`

- [ ] **Step 3: Write minimal implementation**

Create `application/domain/model/job_run/job_run_result.py`:

```python
"""Define the JobRunResult value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class JobRunResult(ValueObject):
    """Execution result metadata for a completed or failed job run.

    Uses a flexible metadata dict so each runtime/job type can define its own keys.
    """

    duration_ms: int | None
    metadata: dict[str, str]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job_run/test_job_run_result.py -v`

Expected: All 5 tests PASS

- [ ] **Step 5: Update `__init__.py` re-exports**

Modify `application/domain/model/job_run/__init__.py` — add `JobRunResult` import and export:

```python
"""JobRun aggregate root and related types."""

from __future__ import annotations

from application.domain.model.job_run.exceptions import (
    InvalidStateTransitionError,
    JobRunNotFoundError,
)
from application.domain.model.job_run.job_run import JobRun
from application.domain.model.job_run.job_run_id import JobRunId
from application.domain.model.job_run.job_run_result import JobRunResult
from application.domain.model.job_run.job_run_status import JobRunStatus
from application.domain.model.job_run.trigger_type import TriggerType

__all__ = [
    "InvalidStateTransitionError",
    "JobRun",
    "JobRunId",
    "JobRunNotFoundError",
    "JobRunResult",
    "JobRunStatus",
    "TriggerType",
]
```

- [ ] **Step 6: Run full test suite to verify nothing broke**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/application/domain/model/job_run/job_run_result.py src/table-maintenance/backend/application/domain/model/job_run/__init__.py src/table-maintenance/backend/tests/application/domain/model/job_run/test_job_run_result.py
git commit -m "feat(domain): add JobRunResult value object"
```

---

## Task 2: Extend JobRun Aggregate with Result Field and Modified Behaviors

**Files:**
- Modify: `application/domain/model/job_run/job_run.py`
- Modify: `application/domain/model/job_run/events.py`
- Modify: `tests/application/domain/model/job_run/test_job_run.py`

- [ ] **Step 1: Write failing tests for updated `mark_completed` and `mark_failed`**

Add to `tests/application/domain/model/job_run/test_job_run.py`:

```python
from application.domain.model.job_run.job_run_result import JobRunResult
from application.domain.model.job_run.events import (
    JobRunCreated,
    JobRunStarted,
    JobRunCompleted,
    JobRunFailed,
)


def _running_job_run() -> JobRun:
    """Create a RUNNING JobRun for testing transitions."""
    run = JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.RUNNING,
        started_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )
    return run


def test_mark_completed_with_result():
    """Verify mark_completed stores result and emits event with result."""
    run = _running_job_run()
    result = JobRunResult(duration_ms=1500, metadata={"expired_snapshots": "42"})
    finished = datetime(2026, 4, 28, 12, 5, tzinfo=UTC)

    run.mark_completed(finished_at=finished, result=result)

    assert run.status == JobRunStatus.COMPLETED
    assert run.finished_at == finished
    assert run.result == result
    events = run.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], JobRunCompleted)
    assert events[0].result == result


def test_mark_failed_with_error_and_result():
    """Verify mark_failed stores error, result, and emits event."""
    run = _running_job_run()
    result = JobRunResult(duration_ms=500, metadata={})
    finished = datetime(2026, 4, 28, 12, 5, tzinfo=UTC)

    run.mark_failed(finished_at=finished, error="Spark OOM", result=result)

    assert run.status == JobRunStatus.FAILED
    assert run.finished_at == finished
    assert run.result == result
    assert run.error == "Spark OOM"
    events = run.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], JobRunFailed)
    assert events[0].error == "Spark OOM"
    assert events[0].result == result


def test_mark_failed_without_result():
    """Verify mark_failed works with result=None."""
    run = _running_job_run()
    finished = datetime(2026, 4, 28, 12, 5, tzinfo=UTC)

    run.mark_failed(finished_at=finished, error="Connection refused")

    assert run.status == JobRunStatus.FAILED
    assert run.error == "Connection refused"
    assert run.result is None


def test_result_defaults_to_none():
    """Verify result and error default to None on new JobRun."""
    run = JobRun(
        id=JobRunId(value="run-1"),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.PENDING,
    )
    assert run.result is None
    assert run.error is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job_run/test_job_run.py -v`

Expected: FAIL — `mark_completed()` doesn't accept `result`, `JobRun` has no `result` or `error` field

- [ ] **Step 3: Update domain events**

Modify `application/domain/model/job_run/events.py` — add `result` to `JobRunCompleted`, add `error` and `result` to `JobRunFailed`:

```python
"""Define domain events for the JobRun aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from base.domain_event import DomainEvent

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.job.cron_expression import CronExpression
    from application.domain.model.job.job_id import JobId
    from application.domain.model.job.job_type import JobType
    from application.domain.model.job.resource_config import ResourceConfig
    from application.domain.model.job.table_reference import TableReference
    from application.domain.model.job_run.job_run_id import JobRunId
    from application.domain.model.job_run.job_run_result import JobRunResult
    from application.domain.model.job_run.trigger_type import TriggerType


@dataclass(frozen=True)
class JobRunCreated(DomainEvent):
    """Raised when a new JobRun is created via the factory method.

    Carries full Job context so downstream handlers (e.g. K8s executor)
    can act without querying the repository.
    """

    run_id: JobRunId
    job_id: JobId
    trigger_type: TriggerType
    job_type: JobType
    table_ref: TableReference
    job_config: dict
    resource_config: ResourceConfig
    cron: CronExpression | None


@dataclass(frozen=True)
class JobRunStarted(DomainEvent):
    """Raised when a JobRun transitions from PENDING to RUNNING."""

    run_id: JobRunId
    job_id: JobId
    started_at: datetime


@dataclass(frozen=True)
class JobRunCompleted(DomainEvent):
    """Raised when a JobRun transitions from RUNNING to COMPLETED."""

    run_id: JobRunId
    job_id: JobId
    finished_at: datetime
    result: JobRunResult


@dataclass(frozen=True)
class JobRunFailed(DomainEvent):
    """Raised when a JobRun transitions to FAILED."""

    run_id: JobRunId
    job_id: JobId
    finished_at: datetime
    error: str
    result: JobRunResult | None


@dataclass(frozen=True)
class JobRunCancelled(DomainEvent):
    """Raised when a JobRun is cancelled."""

    run_id: JobRunId
    job_id: JobId
```

- [ ] **Step 4: Update JobRun aggregate**

Modify `application/domain/model/job_run/job_run.py`:

```python
"""Define the JobRun aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from base.aggregate_root import AggregateRoot

from application.domain.model.job_run.events import (
    JobRunCancelled,
    JobRunCompleted,
    JobRunCreated,
    JobRunFailed,
    JobRunStarted,
)
from application.domain.model.job_run.exceptions import InvalidStateTransitionError
from application.domain.model.job_run.job_run_id import JobRunId
from application.domain.model.job_run.job_run_status import JobRunStatus
from application.domain.model.job_run.trigger_type import TriggerType

if TYPE_CHECKING:
    from datetime import datetime

    from application.domain.model.job.cron_expression import CronExpression
    from application.domain.model.job.job_id import JobId
    from application.domain.model.job.job_type import JobType
    from application.domain.model.job.resource_config import ResourceConfig
    from application.domain.model.job.table_reference import TableReference
    from application.domain.model.job_run.job_run_result import JobRunResult


@dataclass(eq=False)
class JobRun(AggregateRoot[JobRunId]):
    """A single execution of a Job — the aggregate root for run history."""

    id: JobRunId
    job_id: JobId
    status: JobRunStatus
    trigger_type: TriggerType = TriggerType.MANUAL
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: JobRunResult | None = None
    error: str | None = None

    @classmethod
    def create(
        cls,
        id: JobRunId,
        job_id: JobId,
        trigger_type: TriggerType,
        started_at: datetime,
        job_type: JobType,
        table_ref: TableReference,
        job_config: dict,
        resource_config: ResourceConfig,
        cron: CronExpression | None = None,
    ) -> JobRun:
        """Create a new PENDING JobRun and register a JobRunCreated event."""
        run = cls(
            id=id,
            job_id=job_id,
            status=JobRunStatus.PENDING,
            trigger_type=trigger_type,
            started_at=started_at,
        )
        run.register_event(
            JobRunCreated(
                run_id=id,
                job_id=job_id,
                trigger_type=trigger_type,
                job_type=job_type,
                table_ref=table_ref,
                job_config=job_config,
                resource_config=resource_config,
                cron=cron,
            )
        )
        return run

    def _transition_to(self, target: JobRunStatus) -> None:
        """Guard and execute a state transition."""
        if not self.status.can_transition_to(target):
            raise InvalidStateTransitionError(self.status.value, target.value)
        self.status = target

    def mark_running(self, started_at: datetime) -> None:
        """Transition from PENDING to RUNNING."""
        self._transition_to(JobRunStatus.RUNNING)
        self.started_at = started_at
        self.register_event(
            JobRunStarted(run_id=self.id, job_id=self.job_id, started_at=started_at)
        )

    def mark_completed(
        self, finished_at: datetime, result: JobRunResult
    ) -> None:
        """Transition from RUNNING to COMPLETED."""
        self._transition_to(JobRunStatus.COMPLETED)
        self.finished_at = finished_at
        self.result = result
        self.register_event(
            JobRunCompleted(
                run_id=self.id,
                job_id=self.job_id,
                finished_at=finished_at,
                result=result,
            )
        )

    def mark_failed(
        self,
        finished_at: datetime,
        error: str,
        result: JobRunResult | None = None,
    ) -> None:
        """Transition from PENDING or RUNNING to FAILED."""
        self._transition_to(JobRunStatus.FAILED)
        self.finished_at = finished_at
        self.error = error
        self.result = result
        self.register_event(
            JobRunFailed(
                run_id=self.id,
                job_id=self.job_id,
                finished_at=finished_at,
                error=error,
                result=result,
            )
        )

    def cancel(self) -> None:
        """Transition from PENDING or RUNNING to CANCELLED."""
        self._transition_to(JobRunStatus.CANCELLED)
        self.register_event(JobRunCancelled(run_id=self.id, job_id=self.job_id))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/domain/model/job_run/ -v`

Expected: All tests PASS

- [ ] **Step 6: Fix any broken event tests**

The existing `tests/application/domain/model/job_run/test_events.py` may need updating since `JobRunCompleted` now requires `result` and `JobRunFailed` requires `error` and `result`. Check and update as needed — pass `result=JobRunResult(duration_ms=None, metadata={})` where `JobRunCompleted` is constructed, and `error="test error"`, `result=None` where `JobRunFailed` is constructed.

- [ ] **Step 7: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/table-maintenance/backend/application/domain/model/job_run/job_run.py src/table-maintenance/backend/application/domain/model/job_run/events.py src/table-maintenance/backend/tests/application/domain/model/job_run/test_job_run.py src/table-maintenance/backend/tests/application/domain/model/job_run/test_events.py
git commit -m "feat(domain): extend JobRun with result, error fields and updated events"
```

---

## Task 3: Add `save` Method to JobRunsRepo

**Files:**
- Modify: `application/port/outbound/job_run/job_runs_repo.py`
- Modify: `adapter/outbound/job_run/job_runs_in_memory_repo.py`
- Modify: `adapter/outbound/job_run/sql/job_runs_sql_repo.py`
- Modify: `adapter/outbound/job_run/sql/job_runs_table.py`
- Modify: `adapter/outbound/job_run/sql/job_run_to_values.py`
- Modify: `adapter/outbound/job_run/sql/row_to_job_run.py`

- [ ] **Step 1: Add `save` to the port interface**

Modify `application/port/outbound/job_run/job_runs_repo.py` — add after `create`:

```python
    @abstractmethod
    def save(self, entity: JobRun) -> JobRun:
        """Persist changes to an existing job run and return it."""
        ...
```

- [ ] **Step 2: Implement `save` in InMemoryRepo**

Modify `adapter/outbound/job_run/job_runs_in_memory_repo.py` — add after `create`:

```python
    def save(self, entity: JobRun) -> JobRun:
        """Overwrite an existing job run in memory."""
        self._runs[entity.id.value] = entity
        return entity
```

- [ ] **Step 3: Update SQL table schema**

Modify `adapter/outbound/job_run/sql/job_runs_table.py`:

```python
"""Define the job_runs SQL table."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table

from adapter.outbound.sql.metadata import metadata
from sqlalchemy.dialects.sqlite import JSON

job_runs_table = Table(
    "job_runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("job_id", String, ForeignKey("jobs.id"), nullable=False),
    Column("status", String, nullable=False),
    Column("trigger_type", String, nullable=False, default="manual"),
    Column("started_at", DateTime(timezone=True), nullable=True),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("error", String, nullable=True),
    Column("result_duration_ms", Integer, nullable=True),
    Column("result_metadata", JSON, nullable=True),
)
```

Note: Check what JSON type the project uses (SQLAlchemy's `JSON` or `sqlite.JSON`). Use the same pattern as other JSONB columns in the codebase. If no JSON columns exist yet, use `sqlalchemy.JSON` which works with both SQLite (tests) and PostgreSQL (production).

- [ ] **Step 4: Update `job_run_to_values`**

Modify `adapter/outbound/job_run/sql/job_run_to_values.py`:

```python
"""Provide the job_run_to_values serializer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.domain.model.job_run import JobRun


def job_run_to_values(run: JobRun) -> dict[str, Any]:
    """Convert a JobRun domain entity to a dict of SQL column values."""
    return {
        "id": run.id.value,
        "job_id": run.job_id.value,
        "status": run.status.value,
        "trigger_type": run.trigger_type.value,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error": run.error,
        "result_duration_ms": run.result.duration_ms if run.result else None,
        "result_metadata": run.result.metadata if run.result else None,
    }
```

- [ ] **Step 5: Update `row_to_job_run`**

Modify `adapter/outbound/job_run/sql/row_to_job_run.py`:

```python
"""Provide the row_to_job_run deserializer."""

from __future__ import annotations

from typing import Any

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus, TriggerType
from application.domain.model.job_run.job_run_result import JobRunResult


def row_to_job_run(row: Any) -> JobRun:
    """Convert a SQL row to a JobRun domain entity."""
    result = None
    if row["result_duration_ms"] is not None or row["result_metadata"] is not None:
        result = JobRunResult(
            duration_ms=row["result_duration_ms"],
            metadata=row["result_metadata"] or {},
        )
    return JobRun(
        id=JobRunId(value=row["id"]),
        job_id=JobId(value=row["job_id"]),
        status=JobRunStatus(row["status"]),
        trigger_type=TriggerType(row["trigger_type"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        error=row["error"],
        result=result,
    )
```

- [ ] **Step 6: Implement `save` in SqlRepo**

Modify `adapter/outbound/job_run/sql/job_runs_sql_repo.py` — add the `save` method and import `update`:

Add to imports: `from sqlalchemy import func, insert, select, update`

Add method after `create`:

```python
    def save(self, entity: JobRun) -> JobRun:
        """Update an existing job run row and return the entity."""
        values = job_run_to_values(entity)
        run_id = values.pop("id")
        stmt = (
            update(job_runs_table)
            .where(job_runs_table.c.id == run_id)
            .values(**values)
        )
        with self._engine.begin() as conn:
            conn.execute(stmt)
        return entity
```

- [ ] **Step 7: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/table-maintenance/backend/application/port/outbound/job_run/job_runs_repo.py src/table-maintenance/backend/adapter/outbound/job_run/job_runs_in_memory_repo.py src/table-maintenance/backend/adapter/outbound/job_run/sql/
git commit -m "feat(outbound): add save method to JobRunsRepo and extend SQL schema for results"
```

---

## Task 4: CompleteJobRun Use Case

**Files:**
- Create: `application/port/inbound/job_run/complete_job_run/input.py`
- Create: `application/port/inbound/job_run/complete_job_run/output.py`
- Create: `application/port/inbound/job_run/complete_job_run/use_case.py`
- Create: `application/port/inbound/job_run/complete_job_run/__init__.py`
- Create: `application/service/job_run/complete_job_run.py`
- Create: `tests/application/service/job_run/test_complete_job_run.py`
- Modify: `application/port/inbound/job_run/__init__.py`
- Modify: `application/port/inbound/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/application/service/job_run/test_complete_job_run.py`:

```python
"""Tests for CompleteJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from application.domain.model.job_run.job_run_result import JobRunResult
from application.port.inbound.job_run.complete_job_run import (
    CompleteJobRunInput,
    CompleteJobRunOutput,
    CompleteJobRunUseCase,
)
from application.service.job_run.complete_job_run import CompleteJobRunService
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo


def _running_job_run(run_id: str = "run-1") -> JobRun:
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.RUNNING,
        started_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )


class TestCompleteJobRunService:
    def test_implements_use_case_interface(self) -> None:
        repo = JobRunsInMemoryRepo()
        service = CompleteJobRunService(repo)
        assert isinstance(service, CompleteJobRunUseCase)

    def test_completes_running_job_run(self) -> None:
        repo = JobRunsInMemoryRepo()
        run = _running_job_run()
        repo.create(run)
        service = CompleteJobRunService(repo)

        result = service.execute(
            CompleteJobRunInput(
                run_id="run-1",
                duration_ms=1500,
                metadata={"expired_snapshots": "42"},
            )
        )

        assert isinstance(result, CompleteJobRunOutput)
        assert result.run_id == "run-1"
        assert result.status == "completed"
        assert result.finished_at is not None

        saved = repo.get(JobRunId(value="run-1"))
        assert saved.status == JobRunStatus.COMPLETED
        assert saved.result == JobRunResult(
            duration_ms=1500, metadata={"expired_snapshots": "42"}
        )

    def test_completes_with_none_duration(self) -> None:
        repo = JobRunsInMemoryRepo()
        repo.create(_running_job_run())
        service = CompleteJobRunService(repo)

        result = service.execute(
            CompleteJobRunInput(run_id="run-1", duration_ms=None, metadata={})
        )

        saved = repo.get(JobRunId(value="run-1"))
        assert saved.result == JobRunResult(duration_ms=None, metadata={})

    def test_raises_on_not_found(self) -> None:
        repo = JobRunsInMemoryRepo()
        service = CompleteJobRunService(repo)
        try:
            service.execute(
                CompleteJobRunInput(run_id="nope", duration_ms=None, metadata={})
            )
            assert False, "Should have raised"
        except Exception:
            pass

    def test_raises_on_invalid_transition(self) -> None:
        repo = JobRunsInMemoryRepo()
        run = JobRun(
            id=JobRunId(value="run-1"),
            job_id=JobId(value="job-1"),
            status=JobRunStatus.PENDING,
        )
        repo.create(run)
        service = CompleteJobRunService(repo)
        try:
            service.execute(
                CompleteJobRunInput(run_id="run-1", duration_ms=None, metadata={})
            )
            assert False, "Should have raised"
        except Exception:
            pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/job_run/test_complete_job_run.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create inbound port files**

Create `application/port/inbound/job_run/complete_job_run/input.py`:

```python
"""Define the CompleteJobRunInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompleteJobRunInput:
    """Input for completing a job run with success result."""

    run_id: str
    duration_ms: int | None
    metadata: dict[str, str]
```

Create `application/port/inbound/job_run/complete_job_run/output.py`:

```python
"""Define the CompleteJobRunOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class CompleteJobRunOutput:
    """Output after completing a job run."""

    run_id: str
    status: str
    finished_at: datetime
```

Create `application/port/inbound/job_run/complete_job_run/use_case.py`:

```python
"""Define the CompleteJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.job_run.complete_job_run.input import CompleteJobRunInput
from application.port.inbound.job_run.complete_job_run.output import CompleteJobRunOutput


class CompleteJobRunUseCase(UseCase[CompleteJobRunInput, CompleteJobRunOutput]):
    """Mark a job run as completed with result metadata."""
```

Create `application/port/inbound/job_run/complete_job_run/__init__.py`:

```python
"""CompleteJobRun use case definition."""

from application.port.inbound.job_run.complete_job_run.input import CompleteJobRunInput
from application.port.inbound.job_run.complete_job_run.output import CompleteJobRunOutput
from application.port.inbound.job_run.complete_job_run.use_case import (
    CompleteJobRunUseCase,
)

__all__ = ["CompleteJobRunInput", "CompleteJobRunOutput", "CompleteJobRunUseCase"]
```

- [ ] **Step 4: Create service implementation**

Create `application/service/job_run/complete_job_run.py`:

```python
"""Define the CompleteJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId, JobRunNotFoundError
from application.domain.model.job_run.job_run_result import JobRunResult
from application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from application.port.inbound.job_run.complete_job_run import (
    CompleteJobRunInput,
    CompleteJobRunOutput,
    CompleteJobRunUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class CompleteJobRunService(CompleteJobRunUseCase):
    """Mark a running job run as completed with result metadata."""

    def __init__(self, repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._repo = repo

    def execute(self, request: CompleteJobRunInput) -> CompleteJobRunOutput:
        """Complete a job run and persist the result."""
        try:
            run = self._repo.get(JobRunId(value=request.run_id))
        except JobRunNotFoundError as e:
            raise AppJobRunNotFoundError(e.run_id) from e
        result = JobRunResult(
            duration_ms=request.duration_ms,
            metadata=request.metadata,
        )
        finished_at = datetime.now(UTC)
        run.mark_completed(finished_at=finished_at, result=result)
        self._repo.save(run)
        return CompleteJobRunOutput(
            run_id=run.id.value,
            status=run.status.value,
            finished_at=finished_at,
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/job_run/test_complete_job_run.py -v`

Expected: All 5 tests PASS

- [ ] **Step 6: Update `__init__.py` re-exports**

Modify `application/port/inbound/job_run/__init__.py` — add:

```python
from application.port.inbound.job_run.complete_job_run import (
    CompleteJobRunInput,
    CompleteJobRunOutput,
    CompleteJobRunUseCase,
)
```

And add to `__all__`: `"CompleteJobRunInput"`, `"CompleteJobRunOutput"`, `"CompleteJobRunUseCase"`.

Modify `application/port/inbound/__init__.py` — add the same imports and `__all__` entries.

- [ ] **Step 7: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/table-maintenance/backend/application/port/inbound/job_run/complete_job_run/ src/table-maintenance/backend/application/service/job_run/complete_job_run.py src/table-maintenance/backend/tests/application/service/job_run/test_complete_job_run.py src/table-maintenance/backend/application/port/inbound/job_run/__init__.py src/table-maintenance/backend/application/port/inbound/__init__.py
git commit -m "feat(job-run): add CompleteJobRun use case"
```

---

## Task 5: FailJobRun Use Case

**Files:**
- Create: `application/port/inbound/job_run/fail_job_run/input.py`
- Create: `application/port/inbound/job_run/fail_job_run/output.py`
- Create: `application/port/inbound/job_run/fail_job_run/use_case.py`
- Create: `application/port/inbound/job_run/fail_job_run/__init__.py`
- Create: `application/service/job_run/fail_job_run.py`
- Create: `tests/application/service/job_run/test_fail_job_run.py`
- Modify: `application/port/inbound/job_run/__init__.py`
- Modify: `application/port/inbound/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/application/service/job_run/test_fail_job_run.py`:

```python
"""Tests for FailJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime

from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from application.domain.model.job_run.job_run_result import JobRunResult
from application.port.inbound.job_run.fail_job_run import (
    FailJobRunInput,
    FailJobRunOutput,
    FailJobRunUseCase,
)
from application.service.job_run.fail_job_run import FailJobRunService
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo


def _running_job_run(run_id: str = "run-1") -> JobRun:
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value="job-1"),
        status=JobRunStatus.RUNNING,
        started_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )


class TestFailJobRunService:
    def test_implements_use_case_interface(self) -> None:
        repo = JobRunsInMemoryRepo()
        service = FailJobRunService(repo)
        assert isinstance(service, FailJobRunUseCase)

    def test_fails_running_job_run_with_error(self) -> None:
        repo = JobRunsInMemoryRepo()
        repo.create(_running_job_run())
        service = FailJobRunService(repo)

        result = service.execute(
            FailJobRunInput(
                run_id="run-1",
                error="Spark OOM",
                duration_ms=500,
                metadata={"stage": "execution"},
            )
        )

        assert isinstance(result, FailJobRunOutput)
        assert result.run_id == "run-1"
        assert result.status == "failed"
        assert result.finished_at is not None

        saved = repo.get(JobRunId(value="run-1"))
        assert saved.status == JobRunStatus.FAILED
        assert saved.error == "Spark OOM"
        assert saved.result == JobRunResult(
            duration_ms=500, metadata={"stage": "execution"}
        )

    def test_fails_with_no_result_metadata(self) -> None:
        repo = JobRunsInMemoryRepo()
        repo.create(_running_job_run())
        service = FailJobRunService(repo)

        result = service.execute(
            FailJobRunInput(
                run_id="run-1",
                error="Connection refused",
                duration_ms=None,
                metadata=None,
            )
        )

        saved = repo.get(JobRunId(value="run-1"))
        assert saved.error == "Connection refused"
        assert saved.result is None

    def test_fails_pending_job_run(self) -> None:
        """PENDING → FAILED is allowed (e.g. submit failure)."""
        repo = JobRunsInMemoryRepo()
        run = JobRun(
            id=JobRunId(value="run-1"),
            job_id=JobId(value="job-1"),
            status=JobRunStatus.PENDING,
        )
        repo.create(run)
        service = FailJobRunService(repo)

        result = service.execute(
            FailJobRunInput(run_id="run-1", error="Submit failed", duration_ms=None, metadata=None)
        )

        assert result.status == "failed"

    def test_raises_on_not_found(self) -> None:
        repo = JobRunsInMemoryRepo()
        service = FailJobRunService(repo)
        try:
            service.execute(
                FailJobRunInput(run_id="nope", error="err", duration_ms=None, metadata=None)
            )
            assert False, "Should have raised"
        except Exception:
            pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/job_run/test_fail_job_run.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create inbound port files**

Create `application/port/inbound/job_run/fail_job_run/input.py`:

```python
"""Define the FailJobRunInput dataclass."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FailJobRunInput:
    """Input for marking a job run as failed."""

    run_id: str
    error: str
    duration_ms: int | None
    metadata: dict[str, str] | None
```

Create `application/port/inbound/job_run/fail_job_run/output.py`:

```python
"""Define the FailJobRunOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class FailJobRunOutput:
    """Output after marking a job run as failed."""

    run_id: str
    status: str
    finished_at: datetime
```

Create `application/port/inbound/job_run/fail_job_run/use_case.py`:

```python
"""Define the FailJobRunUseCase interface."""

from __future__ import annotations

from base.use_case import UseCase
from application.port.inbound.job_run.fail_job_run.input import FailJobRunInput
from application.port.inbound.job_run.fail_job_run.output import FailJobRunOutput


class FailJobRunUseCase(UseCase[FailJobRunInput, FailJobRunOutput]):
    """Mark a job run as failed with error details."""
```

Create `application/port/inbound/job_run/fail_job_run/__init__.py`:

```python
"""FailJobRun use case definition."""

from application.port.inbound.job_run.fail_job_run.input import FailJobRunInput
from application.port.inbound.job_run.fail_job_run.output import FailJobRunOutput
from application.port.inbound.job_run.fail_job_run.use_case import FailJobRunUseCase

__all__ = ["FailJobRunInput", "FailJobRunOutput", "FailJobRunUseCase"]
```

- [ ] **Step 4: Create service implementation**

Create `application/service/job_run/fail_job_run.py`:

```python
"""Define the FailJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId, JobRunNotFoundError
from application.domain.model.job_run.job_run_result import JobRunResult
from application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from application.port.inbound.job_run.fail_job_run import (
    FailJobRunInput,
    FailJobRunOutput,
    FailJobRunUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class FailJobRunService(FailJobRunUseCase):
    """Mark a job run as failed with error details."""

    def __init__(self, repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._repo = repo

    def execute(self, request: FailJobRunInput) -> FailJobRunOutput:
        """Fail a job run and persist the error."""
        try:
            run = self._repo.get(JobRunId(value=request.run_id))
        except JobRunNotFoundError as e:
            raise AppJobRunNotFoundError(e.run_id) from e
        result = None
        if request.duration_ms is not None or request.metadata is not None:
            result = JobRunResult(
                duration_ms=request.duration_ms,
                metadata=request.metadata or {},
            )
        finished_at = datetime.now(UTC)
        run.mark_failed(finished_at=finished_at, error=request.error, result=result)
        self._repo.save(run)
        return FailJobRunOutput(
            run_id=run.id.value,
            status=run.status.value,
            finished_at=finished_at,
        )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/job_run/test_fail_job_run.py -v`

Expected: All 5 tests PASS

- [ ] **Step 6: Update `__init__.py` re-exports**

Modify `application/port/inbound/job_run/__init__.py` — add:

```python
from application.port.inbound.job_run.fail_job_run import (
    FailJobRunInput,
    FailJobRunOutput,
    FailJobRunUseCase,
)
```

And add to `__all__`: `"FailJobRunInput"`, `"FailJobRunOutput"`, `"FailJobRunUseCase"`.

Modify `application/port/inbound/__init__.py` — add the same imports and `__all__` entries.

- [ ] **Step 7: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add src/table-maintenance/backend/application/port/inbound/job_run/fail_job_run/ src/table-maintenance/backend/application/service/job_run/fail_job_run.py src/table-maintenance/backend/tests/application/service/job_run/test_fail_job_run.py src/table-maintenance/backend/application/port/inbound/job_run/__init__.py src/table-maintenance/backend/application/port/inbound/__init__.py
git commit -m "feat(job-run): add FailJobRun use case"
```

---

## Task 6: Callback API Endpoints

**Files:**
- Create: `adapter/inbound/web/job_run/complete_job_run.py`
- Create: `adapter/inbound/web/job_run/fail_job_run.py`
- Modify: `adapter/inbound/web/job_run/dto.py`
- Modify: `adapter/inbound/web/job_run/__init__.py`
- Modify: `bootstrap/dependencies/use_cases.py`

- [ ] **Step 1: Add request/response DTOs**

Modify `adapter/inbound/web/job_run/dto.py`:

```python
"""Define JobRun API DTOs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobRunApiResponse(BaseModel):
    """Response body representing a job run."""

    run_id: str
    job_id: str
    status: str
    trigger_type: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None = None
    result_duration_ms: int | None = None
    result_metadata: dict[str, str] | None = None


class CompleteJobRunRequest(BaseModel):
    """Request body for completing a job run."""

    duration_ms: int | None = None
    metadata: dict[str, str] | None = None


class FailJobRunRequest(BaseModel):
    """Request body for failing a job run."""

    error: str
    duration_ms: int | None = None
    metadata: dict[str, str] | None = None


class JobRunCallbackResponse(BaseModel):
    """Response body after a callback state transition."""

    run_id: str
    status: str
    finished_at: datetime
```

- [ ] **Step 2: Add DI providers for new use cases**

Modify `bootstrap/dependencies/use_cases.py` — add imports:

```python
from application.service.job_run.complete_job_run import CompleteJobRunService
from application.service.job_run.fail_job_run import FailJobRunService
```

Add to TYPE_CHECKING imports:

```python
    from application.port.inbound import (
        ...
        CompleteJobRunUseCase,
        FailJobRunUseCase,
    )
```

Add provider functions:

```python
def get_complete_job_run_use_case(
    repo: JobRunsRepo = Depends(get_job_runs_repo),
) -> CompleteJobRunUseCase:
    """Provide the CompleteJobRun use case with injected dependencies."""
    return CompleteJobRunService(repo)


def get_fail_job_run_use_case(
    repo: JobRunsRepo = Depends(get_job_runs_repo),
) -> FailJobRunUseCase:
    """Provide the FailJobRun use case with injected dependencies."""
    return FailJobRunService(repo)
```

- [ ] **Step 3: Create complete_job_run endpoint**

Create `adapter/inbound/web/job_run/complete_job_run.py`:

```python
"""POST /runs/{run_id}/complete endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from adapter.inbound.web.job_run.dto import (
    CompleteJobRunRequest,
    JobRunCallbackResponse,
)
from application.exceptions import JobRunNotFoundError
from application.port.inbound.job_run.complete_job_run import (
    CompleteJobRunInput,
    CompleteJobRunUseCase,
)
from bootstrap.dependencies.use_cases import get_complete_job_run_use_case

router = APIRouter()


@router.post("/runs/{run_id}/complete", response_model=JobRunCallbackResponse)
def complete_job_run(
    run_id: str,
    body: CompleteJobRunRequest,
    use_case: CompleteJobRunUseCase = Depends(get_complete_job_run_use_case),
) -> JobRunCallbackResponse:
    """Mark a job run as completed with result metadata."""
    try:
        result = use_case.execute(
            CompleteJobRunInput(
                run_id=run_id,
                duration_ms=body.duration_ms,
                metadata=body.metadata or {},
            )
        )
    except JobRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return JobRunCallbackResponse(
        run_id=result.run_id,
        status=result.status,
        finished_at=result.finished_at,
    )
```

- [ ] **Step 4: Create fail_job_run endpoint**

Create `adapter/inbound/web/job_run/fail_job_run.py`:

```python
"""POST /runs/{run_id}/fail endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from adapter.inbound.web.job_run.dto import (
    FailJobRunRequest,
    JobRunCallbackResponse,
)
from application.exceptions import JobRunNotFoundError
from application.port.inbound.job_run.fail_job_run import (
    FailJobRunInput,
    FailJobRunUseCase,
)
from bootstrap.dependencies.use_cases import get_fail_job_run_use_case

router = APIRouter()


@router.post("/runs/{run_id}/fail", response_model=JobRunCallbackResponse)
def fail_job_run(
    run_id: str,
    body: FailJobRunRequest,
    use_case: FailJobRunUseCase = Depends(get_fail_job_run_use_case),
) -> JobRunCallbackResponse:
    """Mark a job run as failed with error details."""
    try:
        result = use_case.execute(
            FailJobRunInput(
                run_id=run_id,
                error=body.error,
                duration_ms=body.duration_ms,
                metadata=body.metadata,
            )
        )
    except JobRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return JobRunCallbackResponse(
        run_id=result.run_id,
        status=result.status,
        finished_at=result.finished_at,
    )
```

- [ ] **Step 5: Register routers**

Modify `adapter/inbound/web/job_run/__init__.py`:

```python
"""JobRun REST API endpoints."""

from fastapi import APIRouter

from adapter.inbound.web.job_run.complete_job_run import router as complete_run_router
from adapter.inbound.web.job_run.fail_job_run import router as fail_run_router
from adapter.inbound.web.job_run.get_job_run import router as get_run_router
from adapter.inbound.web.job_run.list_job_runs import router as list_runs_router
from adapter.inbound.web.job_run.trigger_job_run import router as create_run_router

router = APIRouter(tags=["job-runs"])
router.include_router(create_run_router)
router.include_router(list_runs_router)
router.include_router(get_run_router)
router.include_router(complete_run_router)
router.include_router(fail_run_router)
```

- [ ] **Step 6: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/adapter/inbound/web/job_run/ src/table-maintenance/backend/bootstrap/dependencies/use_cases.py
git commit -m "feat(web): add callback endpoints POST /runs/{run_id}/complete and /fail"
```

---

## Task 7: Update GetJobRun to Return Result Fields

**Files:**
- Modify: `application/port/inbound/job_run/get_job_run/output.py`
- Modify: `application/service/job_run/get_job_run.py`
- Modify: `adapter/inbound/web/job_run/get_job_run.py`

- [ ] **Step 1: Update GetJobRunOutput**

Modify `application/port/inbound/job_run/get_job_run/output.py`:

```python
"""Define the GetJobRunOutput dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True)
class GetJobRunOutput:
    """Output for the GetJobRun use case."""

    run_id: str
    job_id: str
    status: str
    trigger_type: str
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    result_duration_ms: int | None
    result_metadata: dict[str, str] | None
```

- [ ] **Step 2: Update GetJobRunService**

Modify `application/service/job_run/get_job_run.py`:

```python
"""Define the GetJobRunService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId, JobRunNotFoundError
from application.exceptions import JobRunNotFoundError as AppJobRunNotFoundError
from application.port.inbound import (
    GetJobRunInput,
    GetJobRunOutput,
    GetJobRunUseCase,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo


class GetJobRunService(GetJobRunUseCase):
    """Retrieves a single JobRun by id."""

    def __init__(self, repo: JobRunsRepo) -> None:
        """Initialize with the job runs repository."""
        self._repo = repo

    def execute(self, request: GetJobRunInput) -> GetJobRunOutput:
        """Retrieve a job run by its identifier."""
        try:
            run = self._repo.get(JobRunId(value=request.run_id))
        except JobRunNotFoundError as e:
            raise AppJobRunNotFoundError(e.run_id) from e
        return GetJobRunOutput(
            run_id=run.id.value,
            job_id=run.job_id.value,
            status=run.status.value,
            trigger_type=run.trigger_type.value,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error=run.error,
            result_duration_ms=run.result.duration_ms if run.result else None,
            result_metadata=run.result.metadata if run.result else None,
        )
```

- [ ] **Step 3: Update web adapter**

Modify `adapter/inbound/web/job_run/get_job_run.py` — update the `JobRunApiResponse` construction to include new fields:

```python
    return JobRunApiResponse(
        run_id=result.run_id,
        job_id=result.job_id,
        status=result.status,
        trigger_type=result.trigger_type,
        started_at=result.started_at,
        finished_at=result.finished_at,
        error=result.error,
        result_duration_ms=result.result_duration_ms,
        result_metadata=result.result_metadata,
    )
```

- [ ] **Step 4: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS. Some existing GetJobRun tests may need updating if they construct `GetJobRunOutput` without the new fields — add `error=None`, `result_duration_ms=None`, `result_metadata=None` where needed.

- [ ] **Step 5: Commit**

```bash
git add src/table-maintenance/backend/application/port/inbound/job_run/get_job_run/output.py src/table-maintenance/backend/application/service/job_run/get_job_run.py src/table-maintenance/backend/adapter/inbound/web/job_run/get_job_run.py
git commit -m "feat(job-run): return result fields in GET /runs/{run_id} response"
```

---

## Task 8: Modify SubmitJobRunService to Mark RUNNING

**Files:**
- Modify: `application/service/job_run/submit_job_run.py`
- Modify: `tests/application/service/job_run/test_submit_job_run.py`

- [ ] **Step 1: Write failing test**

Add to `tests/application/service/job_run/test_submit_job_run.py`:

```python
from application.domain.model.job import JobId
from application.domain.model.job_run import JobRun, JobRunId, JobRunStatus
from adapter.outbound.job_run.job_runs_in_memory_repo import JobRunsInMemoryRepo
from datetime import UTC, datetime


def _pending_job_run(run_id: str = "r1") -> JobRun:
    return JobRun(
        id=JobRunId(value=run_id),
        job_id=JobId(value="j1"),
        status=JobRunStatus.PENDING,
        started_at=datetime(2026, 4, 28, 12, 0, tzinfo=UTC),
    )


class TestSubmitJobRunServiceMarksRunning:
    def test_marks_job_run_as_running_after_submit(self) -> None:
        executor = MagicMock()
        repo = JobRunsInMemoryRepo()
        repo.create(_pending_job_run())
        service = SubmitJobRunService(executor, repo)
        inp = _make_input()

        service.execute(inp)

        saved = repo.get(JobRunId(value="r1"))
        assert saved.status == JobRunStatus.RUNNING

    def test_does_not_mark_running_if_submit_fails(self) -> None:
        executor = MagicMock()
        executor.submit.side_effect = RuntimeError("K8s unreachable")
        repo = JobRunsInMemoryRepo()
        repo.create(_pending_job_run())
        service = SubmitJobRunService(executor, repo)
        inp = _make_input()

        try:
            service.execute(inp)
        except RuntimeError:
            pass

        saved = repo.get(JobRunId(value="r1"))
        assert saved.status == JobRunStatus.PENDING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/service/job_run/test_submit_job_run.py -v`

Expected: FAIL — `SubmitJobRunService.__init__()` doesn't accept `repo` parameter

- [ ] **Step 3: Update SubmitJobRunService**

Modify `application/service/job_run/submit_job_run.py`:

```python
"""Define the SubmitJobRunService."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from application.domain.model.job_run import JobRunId
from application.port.inbound.job_run.submit_job_run import (
    SubmitJobRunInput,
    SubmitJobRunUseCase,
)
from application.port.outbound.job_run.submit_job_run.input import (
    SubmitJobRunInput as SubmitJobRunGatewayInput,
)

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_runs_repo import JobRunsRepo
    from application.port.outbound.job_run.submit_job_run.gateway import (
        SubmitJobRunGateway,
    )


class SubmitJobRunService(SubmitJobRunUseCase):
    """Map a SubmitJobRunInput to a SubmitJobRunGatewayInput and delegate to the executor."""

    def __init__(self, executor: SubmitJobRunGateway, repo: JobRunsRepo) -> None:
        """Initialize with the job run executor and repository."""
        self._executor = executor
        self._repo = repo

    def execute(self, request: SubmitJobRunInput) -> None:
        """Build a SubmitJobRunGatewayInput from the input, submit it, and mark as RUNNING."""
        submission = SubmitJobRunGatewayInput(
            run_id=request.run_id,
            job_id=request.job_id,
            job_type=request.job_type,
            catalog=request.catalog,
            table=request.table,
            job_config=request.job_config,
            driver_memory=request.driver_memory,
            executor_memory=request.executor_memory,
            executor_instances=request.executor_instances,
            cron_expression=request.cron_expression,
        )
        self._executor.submit(submission)
        run = self._repo.get(JobRunId(value=request.run_id))
        run.mark_running(started_at=datetime.now(UTC))
        self._repo.save(run)
```

- [ ] **Step 4: Fix existing tests**

The existing `TestSubmitJobRunService` tests create `SubmitJobRunService(executor)` with one arg. Update them to `SubmitJobRunService(executor, MagicMock())` — mock the repo since those tests don't care about the RUNNING transition.

- [ ] **Step 5: Update DI in bootstrap**

Check `bootstrap/dependencies/use_cases.py` or wherever `SubmitJobRunService` is wired. If there's a DI provider, update it. If `SubmitJobRunService` is constructed in `JobRunCreatedHandler`, check `bootstrap/messaging.py` or wherever the handler is wired.

Look at how `JobRunCreatedHandler` constructs `SubmitJobRunUseCase`. The handler is likely wired in `bootstrap/messaging.py`. Update the construction to include `repo`:

```python
SubmitJobRunService(executor, job_runs_repo)
```

- [ ] **Step 6: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/table-maintenance/backend/application/service/job_run/submit_job_run.py src/table-maintenance/backend/tests/application/service/job_run/test_submit_job_run.py src/table-maintenance/backend/bootstrap/
git commit -m "feat(job-run): mark job run as RUNNING after successful submit"
```

---

## Task 9: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS

- [ ] **Step 2: Run type checker**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ty check`

Expected: No errors

- [ ] **Step 3: Run linter**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check .`

Expected: No errors

- [ ] **Step 4: Run import linter**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

Expected: No violations

- [ ] **Step 5: Run architecture tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/architecture/ -v`

Expected: All architecture guard tests PASS
