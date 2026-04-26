# Event Chain Integration & Error Scenario Tests

Date: 2026-04-26

## Problem

Each handler in the outbox event chain has unit tests with MagicMock, but no test verifies the full chain works end-to-end with real objects:

```
ScheduleJobsService → outbox → JobTriggeredHandler → JobRun + JobRunCreated
  → outbox → JobRunCreatedHandler → executor.submit()
```

Error scenarios (executor failure, serialization edge cases, outbox idempotency) are also untested.

## Decisions

- **Approach**: Progressive layering — test the middle first (outbox → handlers), extend to full chain (scheduler → executor), then add error scenarios.
- **Executor boundary**: Use `JobRunInMemoryExecutor` as the terminus. K8s manifest generation is already covered by unit tests.
- **Database**: SQLite in-memory for all integration tests. Real `EventOutboxSqlRepo`, `JobsSqlRepo`, `JobRunsSqlRepo`.
- **No mocks**: All objects are real except the executor (which is `InMemoryExecutor` by design).

## Design

### Step 1: Outbox → Handlers → Executor

File: `tests/test_event_chain_publish.py`

Wiring:
- `EventOutboxSqlRepo` (SQLite in-memory)
- `EventSerializer` (real)
- `EventDispatcher` (real, both handlers registered)
- `JobTriggeredHandler` (real, with `JobRunsSqlRepo` and `EventOutboxSqlRepo`)
- `JobRunCreatedHandler` (real, with `JobRunInMemoryExecutor`)
- `PublishEventsService` (real)

Tests:

1. **`test_job_triggered_flows_to_pending_job_run`**
   - Manually insert a `JobTriggered` outbox entry.
   - Call `PublishEventsService.execute()` once.
   - Assert: `JobRunsSqlRepo` contains one PENDING JobRun. Outbox has a new `JobRunCreated` entry.

2. **`test_job_run_created_flows_to_executor_submit`**
   - Manually insert a `JobRunCreated` outbox entry.
   - Call `PublishEventsService.execute()` once.
   - Assert: `InMemoryExecutor.submitted` has one `JobSubmission` with correct fields.

3. **`test_two_ticks_complete_full_chain`**
   - Insert one `JobTriggered` outbox entry.
   - First `execute()` → produces `JobRunCreated`.
   - Second `execute()` → executor receives submission.
   - Assert: Full two-hop chain completes. Submission fields match original event data.

### Step 2: Scheduler → Outbox → Two Hops → Executor

File: `tests/test_event_chain_scheduler.py`

Extends Step 1 wiring with:
- `JobsSqlRepo` (SQLite in-memory, pre-populated with due Jobs)
- `ScheduleJobsService` (real)

Tests:

1. **`test_scheduler_tick_triggers_full_chain`**
   - Create a due Job (cron + next_run_at in the past) in DB.
   - `ScheduleJobsService.execute()` → outbox gets `JobTriggered`.
   - `PublishEventsService.execute()` twice (two hops).
   - Assert: executor receives `JobSubmission` with job_type, catalog, table, resource_config matching the original Job.

2. **`test_scheduler_with_custom_resource_config`**
   - Create Job with `ResourceConfig(driver_memory="4g", executor_instances=3)`.
   - Run full chain.
   - Assert: submission has `driver_memory="4g"`, `executor_instances=3`.

3. **`test_scheduler_skips_paused_job`**
   - Create a paused Job.
   - `ScheduleJobsService.execute()` → triggered_count == 0.
   - Assert: outbox empty, executor received nothing.

4. **`test_scheduler_respects_max_active_runs`**
   - Create Job (max_active_runs=1), pre-insert one PENDING JobRun.
   - `ScheduleJobsService.execute()` → triggered_count == 0.

### Step 3a: Executor Failure

File: `tests/test_error_executor_failure.py`

Uses a `FailingExecutor` that raises `RuntimeError` on `submit()`.

Tests:

1. **`test_executor_failure_does_not_lose_job_run`**
   - Insert `JobRunCreated` entry, wire FailingExecutor.
   - `PublishEventsService.execute()` — dispatch raises.
   - Assert: The JobRun created by the first hop is still in DB (persisted before the second hop).

2. **`test_executor_failure_entry_stays_unpublished`**
   - Same setup. Verify: if dispatch raises, the outbox entry remains unpublished (retryable on next tick).

### Step 3b: Serializer Edge Cases

File: `tests/test_error_serializer_edge_cases.py`

Tests:

1. **`test_roundtrip_job_triggered_with_empty_job_config`** — `job_config={}` survives serialize/deserialize.
2. **`test_roundtrip_job_triggered_with_large_job_config`** — 100-key dict round-trips correctly.
3. **`test_roundtrip_job_triggered_with_special_chars`** — Chinese characters, emoji, backslashes in values.
4. **`test_roundtrip_job_run_created_with_cron_none`** — `cron=None` round-trips to None.
5. **`test_roundtrip_job_run_created_with_resource_config`** — `ResourceConfig` fields preserved.
6. **`test_deserialize_unknown_event_type_raises`** — Unknown event type key raises `KeyError`.

### Step 3c: Outbox Idempotency

File: `tests/test_error_outbox_idempotency.py`

Tests:

1. **`test_duplicate_job_triggered_creates_two_job_runs`**
   - Two `JobTriggered` outbox entries for the same Job.
   - Publish both → two distinct JobRuns created (IDs differ due to random hex).

2. **`test_published_entries_not_re_dispatched`**
   - One `execute()` marks entries published.
   - Second `execute()` → `published_count == 0`, executor receives nothing new.

## Shared Test Fixture

All Step 1/2/3a/3c tests share a common wiring helper:

```python
def build_event_chain(executor=None):
    """Wire the full outbox event chain with SQLite in-memory.

    Returns a namespace with: engine, jobs_repo, job_runs_repo, outbox_repo,
    serializer, dispatcher, executor, publish_service.
    """
```

This helper creates the engine, initializes tables, wires handlers and dispatcher, and returns all components for test assertions.

## File Layout

```
tests/
├── test_event_chain_publish.py      # Step 1: outbox → handlers → executor
├── test_event_chain_scheduler.py    # Step 2: scheduler → full chain
├── test_error_executor_failure.py   # Step 3a: executor failure behavior
├── test_error_serializer_edge_cases.py  # Step 3b: serializer boundaries
└── test_error_outbox_idempotency.py     # Step 3c: duplicate/replay behavior
```

## Implementation Order

1. Build shared fixture helper
2. Step 1 tests (3 tests)
3. Step 2 tests (4 tests)
4. Step 3b tests (6 tests) — pure unit, no fixture dependency
5. Step 3a tests (2 tests) — needs FailingExecutor
6. Step 3c tests (2 tests) — reuses shared fixture
