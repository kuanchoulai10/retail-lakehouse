# DTO Naming Convention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename all DTO classes across layers to include layer-specific suffixes, then add architecture tests to enforce the convention.

**Architecture:** Mechanical rename refactor across three layers (inbound port, outbound port, web adapter). Each task renames one domain's classes, updates all references, and verifies tests pass. Architecture test added last as a guard rail.

**Tech Stack:** Python, pytest, ast module (for architecture test)

**Spec:** `docs/superpowers/specs/2026-04-28-dto-naming-convention-design.md`

---

## Naming Convention Summary

| Layer | File | Old Suffix | New Suffix | Allowed Additional Suffixes |
|-------|------|-----------|------------|---------------------------|
| Inbound port | `input.py` | `Input` | `UseCaseInput` | — |
| Inbound port | `output.py` | `Output`/`Result` | `UseCaseOutput` | `UseCaseOutputItem` |
| Outbound port | `input.py` | `Input` | `GatewayInput` | — |
| Outbound port | `output.py` | `Output` | `GatewayOutput` | — |
| Web adapter | `dto.py` | `ApiRequest`/`ApiResponse` | same | — |

**Prefix rule:** Class name prefix must start with the PascalCase form of the parent directory name.

**Special cases:**
- `ScheduleJobsResult` → `ScheduleJobsUseCaseOutput` (standardize suffix)
- `PublishEventsResult` → `PublishEventsUseCaseOutput` (standardize suffix)
- `GetTableSchemaOutput` → `GetTableSchemaUseCaseOutput` (prefix starts with `GetTable`, allowed)
- `GetTableSchemaFieldOutput` → `GetTableSchemaFieldUseCaseOutput` (prefix starts with `GetTable`, allowed)
- `*OutputItem` → `*UseCaseOutputItem` (e.g., `ListJobsOutputItem` → `ListJobsUseCaseOutputItem`)
- `JobApiRequest` → `CreateJobApiRequest` (add missing verb prefix)

## Working Directory

All paths are relative to `src/table-maintenance/backend/`.

## Rename Strategy

For each rename task:
1. Rename class in its definition file (`input.py`, `output.py`, or `dto.py`)
2. Update the use case directory's `__init__.py` re-export
3. Update the domain-level `__init__.py` re-export
4. Update the top-level inbound `__init__.py` re-export
5. Update the use case interface (`use_case.py`) type annotations
6. Update the service implementation
7. Update web adapter routes
8. Update test files
9. Run tests to verify

---

### Task 1: Rename outbound port — `SubmitJobRunInput` → `SubmitJobRunGatewayInput`

**Files:**
- Modify: `application/port/outbound/job_run/submit_job_run/input.py` (class definition)
- Modify: `application/port/outbound/job_run/submit_job_run/__init__.py` (re-export)
- Modify: `application/port/outbound/job_run/submit_job_run/gateway.py` (type annotation)
- Modify: `application/port/outbound/job_run/__init__.py` (re-export)
- Modify: `application/port/outbound/__init__.py` (re-export)
- Modify: `adapter/outbound/job_run/submit_job_run_in_memory_gateway.py` (import + usage)
- Modify: `adapter/outbound/job_run/k8s/submit_job_run_k8s_gateway.py` (import + usage)
- Modify: `adapter/outbound/job_run/k8s/manifest.py` (import + usage)
- Modify: `application/service/job_run/submit_job_run.py` (import alias — remove alias since name is now unambiguous)
- Modify: `tests/application/service/job_run/test_submit_job_run.py` (import alias — remove alias)
- Modify: `tests/adapter/outbound/job_run/test_submit_job_run_in_memory_gateway.py`
- Modify: `tests/adapter/outbound/job_run/k8s/test_manifest.py`
- Modify: `tests/adapter/outbound/job_run/k8s/test_submit_job_run_k8s_gateway.py`
- Modify: `tests/application/port/outbound/job_run/test_submit_job_run_input.py`
- Modify: `tests/test_event_chain_publish.py`
- Modify: `tests/test_error_executor_failure.py`

- [ ] **Step 1: Rename class definition**

In `application/port/outbound/job_run/submit_job_run/input.py`, rename `SubmitJobRunInput` → `SubmitJobRunGatewayInput`. Update docstring and module docstring.

- [ ] **Step 2: Update outbound port re-exports**

In these `__init__.py` files, replace `SubmitJobRunInput` with `SubmitJobRunGatewayInput`:
- `application/port/outbound/job_run/submit_job_run/__init__.py`
- `application/port/outbound/job_run/__init__.py`
- `application/port/outbound/__init__.py`

- [ ] **Step 3: Update gateway interface**

In `application/port/outbound/job_run/submit_job_run/gateway.py`, update the type annotation from `SubmitJobRunInput` to `SubmitJobRunGatewayInput`.

- [ ] **Step 4: Update adapter implementations**

In these files, update imports and all references from `SubmitJobRunInput` to `SubmitJobRunGatewayInput`:
- `adapter/outbound/job_run/submit_job_run_in_memory_gateway.py`
- `adapter/outbound/job_run/k8s/submit_job_run_k8s_gateway.py`
- `adapter/outbound/job_run/k8s/manifest.py`

- [ ] **Step 5: Update service — remove import alias**

In `application/service/job_run/submit_job_run.py`, the current import is:
```python
from application.port.outbound.job_run import SubmitJobRunInput as SubmitJobRunGatewayInput
```
Replace with a direct import (no alias needed now):
```python
from application.port.outbound.job_run import SubmitJobRunGatewayInput
```
Update all usages of the old alias in this file (should already be `SubmitJobRunGatewayInput`).

- [ ] **Step 6: Update test files**

Update imports and references in:
- `tests/application/service/job_run/test_submit_job_run.py` (remove alias, use direct import)
- `tests/adapter/outbound/job_run/test_submit_job_run_in_memory_gateway.py`
- `tests/adapter/outbound/job_run/k8s/test_manifest.py`
- `tests/adapter/outbound/job_run/k8s/test_submit_job_run_k8s_gateway.py`
- `tests/application/port/outbound/job_run/test_submit_job_run_input.py`
- `tests/test_event_chain_publish.py`
- `tests/test_error_executor_failure.py`

- [ ] **Step 7: Run tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(outbound-port): rename SubmitJobRunInput to SubmitJobRunGatewayInput"
```

---

### Task 2: Rename web adapter — job domain

| Old | New |
|-----|-----|
| `JobApiRequest` | `CreateJobApiRequest` |

**Note:** `JobApiResponse` and `UpdateJobApiRequest` already follow the convention and stay as-is.

**Files:**
- Modify: `adapter/inbound/web/job/dto.py` (class definition)
- Modify: `adapter/inbound/web/job/create_job.py` (import + usage)
- Modify: `tests/application/domain/model/job/test_job_request.py` (import + usage)

- [ ] **Step 1: Rename class**

In `adapter/inbound/web/job/dto.py`, rename `JobApiRequest` → `CreateJobApiRequest`. Update class docstring to say "Request body for creating a new job."

- [ ] **Step 2: Update route handler**

In `adapter/inbound/web/job/create_job.py`, update import and parameter type from `JobApiRequest` to `CreateJobApiRequest`.

- [ ] **Step 3: Update test file**

In `tests/application/domain/model/job/test_job_request.py`, update import and all instantiations from `JobApiRequest` to `CreateJobApiRequest`.

- [ ] **Step 4: Run tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(web): rename JobApiRequest to CreateJobApiRequest"
```

---

### Task 2.1: Rename web adapter — catalog domain

All catalog response DTOs currently lack the `Api` infix. Add it:

| Old | New |
|-----|-----|
| `SchemaFieldResponse` | `SchemaFieldApiResponse` |
| `SchemaResponse` | `SchemaApiResponse` |
| `NamespacesResponse` | `NamespacesApiResponse` |
| `TablesResponse` | `TablesApiResponse` |
| `TableDetailResponse` | `TableDetailApiResponse` |
| `SnapshotResponse` | `SnapshotApiResponse` |
| `SnapshotsResponse` | `SnapshotsApiResponse` |
| `BranchResponse` | `BranchApiResponse` |
| `BranchesResponse` | `BranchesApiResponse` |
| `TagResponse` | `TagApiResponse` |
| `TagsResponse` | `TagsApiResponse` |

**Files:**
- Modify: `adapter/inbound/web/catalog/dto.py` (all class definitions)
- Modify: `adapter/inbound/web/catalog/get_table.py` (imports + usage)
- Modify: `adapter/inbound/web/catalog/list_tables.py` (imports + usage)
- Modify: `adapter/inbound/web/catalog/list_namespaces.py` (imports + usage)
- Modify: `adapter/inbound/web/catalog/list_branches.py` (imports + usage)
- Modify: `adapter/inbound/web/catalog/list_tags.py` (imports + usage)
- Modify: `adapter/inbound/web/catalog/list_snapshots.py` (imports + usage)

**Note:** No test files reference these DTOs directly (verified via grep).

- [ ] **Step 1: Rename class definitions**

In `adapter/inbound/web/catalog/dto.py`, rename all 11 classes per the table above. The internal type references must also be updated:
- `SchemaResponse.fields: list[SchemaFieldResponse]` → `SchemaApiResponse.fields: list[SchemaFieldApiResponse]`
- `TableDetailResponse.schema_: SchemaResponse` → `TableDetailApiResponse.schema_: SchemaApiResponse`
- `SnapshotsResponse.snapshots: list[SnapshotResponse]` → `SnapshotsApiResponse.snapshots: list[SnapshotApiResponse]`
- `BranchesResponse.branches: list[BranchResponse]` → `BranchesApiResponse.branches: list[BranchApiResponse]`
- `TagsResponse.tags: list[TagResponse]` → `TagsApiResponse.tags: list[TagApiResponse]`

- [ ] **Step 2: Update route handlers**

For each catalog route file, update the import statement and the `response_model` / return type annotations:
- `get_table.py`: `TableDetailResponse` → `TableDetailApiResponse`
- `list_tables.py`: `TablesResponse` → `TablesApiResponse`
- `list_namespaces.py`: `NamespacesResponse` → `NamespacesApiResponse`
- `list_branches.py`: `BranchesResponse`, `BranchResponse` → `BranchesApiResponse`, `BranchApiResponse`
- `list_tags.py`: `TagsResponse`, `TagResponse` → `TagsApiResponse`, `TagApiResponse`
- `list_snapshots.py`: `SnapshotsResponse`, `SnapshotResponse` → `SnapshotsApiResponse`, `SnapshotApiResponse`

- [ ] **Step 3: Run tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(web): add Api infix to catalog response DTOs"
```

---

### Task 2.2: Rename web adapter — job_run domain

| Old | New |
|-----|-----|
| `CompleteJobRunRequest` | `CompleteJobRunApiRequest` |
| `FailJobRunRequest` | `FailJobRunApiRequest` |
| `JobRunCallbackResponse` | `JobRunCallbackApiResponse` |

**Note:** `JobRunApiResponse` already follows the convention and stays as-is.

**Files:**
- Modify: `adapter/inbound/web/job_run/dto.py` (class definitions)
- Modify: `adapter/inbound/web/job_run/complete_job_run.py` (imports + usage)
- Modify: `adapter/inbound/web/job_run/fail_job_run.py` (imports + usage)
- Modify: `adapter/inbound/web/job_run/get_job_run.py` (imports + usage if any)
- Modify: `adapter/inbound/web/job_run/list_job_runs.py` (imports + usage if any)

- [ ] **Step 1: Rename class definitions**

In `adapter/inbound/web/job_run/dto.py`:
- `CompleteJobRunRequest` → `CompleteJobRunApiRequest`
- `FailJobRunRequest` → `FailJobRunApiRequest`
- `JobRunCallbackResponse` → `JobRunCallbackApiResponse`

Update class docstrings to match new names.

- [ ] **Step 2: Update route handlers**

Update imports and parameter/response type annotations in:
- `complete_job_run.py`: uses `CompleteJobRunRequest` and `JobRunCallbackResponse`
- `fail_job_run.py`: uses `FailJobRunRequest` and `JobRunCallbackResponse`
- `get_job_run.py` and `list_job_runs.py`: only check for any references and update if found

- [ ] **Step 3: Run tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(web): add Api infix to job_run DTOs"
```

---

### Task 3: Rename inbound port — job domain

Rename all Input/Output classes in `application/port/inbound/job/`:

| Old | New |
|-----|-----|
| `CreateJobInput` | `CreateJobUseCaseInput` |
| `CreateJobOutput` | `CreateJobUseCaseOutput` |
| `GetJobInput` | `GetJobUseCaseInput` |
| `GetJobOutput` | `GetJobUseCaseOutput` |
| `UpdateJobInput` | `UpdateJobUseCaseInput` |
| `UpdateJobOutput` | `UpdateJobUseCaseOutput` |
| `DeleteJobInput` | `DeleteJobUseCaseInput` |
| `DeleteJobOutput` | `DeleteJobUseCaseOutput` |
| `ListJobsInput` | `ListJobsUseCaseInput` |
| `ListJobsOutput` | `ListJobsUseCaseOutput` |
| `ListJobsOutputItem` | `ListJobsUseCaseOutputItem` |

**Files:**
- Modify: `application/port/inbound/job/create_job/input.py`
- Modify: `application/port/inbound/job/create_job/output.py`
- Modify: `application/port/inbound/job/create_job/__init__.py`
- Modify: `application/port/inbound/job/create_job/use_case.py`
- Modify: `application/port/inbound/job/get_job/input.py`
- Modify: `application/port/inbound/job/get_job/output.py`
- Modify: `application/port/inbound/job/get_job/__init__.py`
- Modify: `application/port/inbound/job/get_job/use_case.py`
- Modify: `application/port/inbound/job/update_job/input.py`
- Modify: `application/port/inbound/job/update_job/output.py`
- Modify: `application/port/inbound/job/update_job/__init__.py`
- Modify: `application/port/inbound/job/update_job/use_case.py`
- Modify: `application/port/inbound/job/delete_job/input.py`
- Modify: `application/port/inbound/job/delete_job/output.py`
- Modify: `application/port/inbound/job/delete_job/__init__.py`
- Modify: `application/port/inbound/job/delete_job/use_case.py`
- Modify: `application/port/inbound/job/list_jobs/input.py`
- Modify: `application/port/inbound/job/list_jobs/output.py`
- Modify: `application/port/inbound/job/list_jobs/__init__.py`
- Modify: `application/port/inbound/job/list_jobs/use_case.py`
- Modify: `application/port/inbound/job/__init__.py`
- Modify: `application/port/inbound/__init__.py`
- Modify: `application/service/job/create_job.py`
- Modify: `application/service/job/get_job.py`
- Modify: `application/service/job/update_job.py`
- Modify: `application/service/job/delete_job.py`
- Modify: `application/service/job/list_jobs.py`
- Modify: `adapter/inbound/web/job/create_job.py`
- Modify: `adapter/inbound/web/job/get_job.py`
- Modify: `adapter/inbound/web/job/update_job.py`
- Modify: `adapter/inbound/web/job/delete_job.py`
- Modify: `adapter/inbound/web/job/list_jobs.py`
- Modify: `tests/adapter/inbound/web/job/test_create_job.py`
- Modify: `tests/adapter/inbound/web/job/test_get_job.py`
- Modify: `tests/adapter/inbound/web/job/test_update_job.py`
- Modify: `tests/adapter/inbound/web/job/test_delete_job.py`
- Modify: `tests/adapter/inbound/web/job/test_list_jobs.py`
- Modify: `tests/application/service/job/test_get_job.py`
- Modify: `tests/application/service/job/test_list_jobs.py`

- [ ] **Step 1: Rename class definitions in input.py and output.py files**

For each use case directory under `application/port/inbound/job/`, rename the class in `input.py` and `output.py`:
- `create_job/input.py`: `CreateJobInput` → `CreateJobUseCaseInput`
- `create_job/output.py`: `CreateJobOutput` → `CreateJobUseCaseOutput`
- `get_job/input.py`: `GetJobInput` → `GetJobUseCaseInput`
- `get_job/output.py`: `GetJobOutput` → `GetJobUseCaseOutput`
- `update_job/input.py`: `UpdateJobInput` → `UpdateJobUseCaseInput`
- `update_job/output.py`: `UpdateJobOutput` → `UpdateJobUseCaseOutput`
- `delete_job/input.py`: `DeleteJobInput` → `DeleteJobUseCaseInput`
- `delete_job/output.py`: `DeleteJobOutput` → `DeleteJobUseCaseOutput`
- `list_jobs/input.py`: `ListJobsInput` → `ListJobsUseCaseInput`
- `list_jobs/output.py`: `ListJobsOutput` → `ListJobsUseCaseOutput`, `ListJobsOutputItem` → `ListJobsUseCaseOutputItem`

Update docstrings in each file to match new class names.

- [ ] **Step 2: Update use case interfaces**

For each use case directory, update `use_case.py` type annotations:
- `create_job/use_case.py`: `UseCase[CreateJobInput, CreateJobOutput]` → `UseCase[CreateJobUseCaseInput, CreateJobUseCaseOutput]`
- `get_job/use_case.py`: same pattern
- `update_job/use_case.py`: same pattern
- `delete_job/use_case.py`: same pattern
- `list_jobs/use_case.py`: same pattern

- [ ] **Step 3: Update re-exports**

Update `__init__.py` re-exports at three levels:
1. Each use case's `__init__.py` (e.g., `create_job/__init__.py`)
2. Domain-level `application/port/inbound/job/__init__.py`
3. Top-level `application/port/inbound/__init__.py`

Replace all old class names with new names in both import statements and `__all__` lists.

- [ ] **Step 4: Update service implementations**

Update imports and type annotations in:
- `application/service/job/create_job.py`
- `application/service/job/get_job.py`
- `application/service/job/update_job.py`
- `application/service/job/delete_job.py`
- `application/service/job/list_jobs.py`

- [ ] **Step 5: Update web adapter routes**

Update imports in:
- `adapter/inbound/web/job/create_job.py`
- `adapter/inbound/web/job/get_job.py`
- `adapter/inbound/web/job/update_job.py`
- `adapter/inbound/web/job/delete_job.py`
- `adapter/inbound/web/job/list_jobs.py`

- [ ] **Step 6: Update test files**

Update imports and references in:
- `tests/adapter/inbound/web/job/test_create_job.py`
- `tests/adapter/inbound/web/job/test_get_job.py`
- `tests/adapter/inbound/web/job/test_update_job.py`
- `tests/adapter/inbound/web/job/test_delete_job.py`
- `tests/adapter/inbound/web/job/test_list_jobs.py`
- `tests/application/service/job/test_get_job.py`
- `tests/application/service/job/test_list_jobs.py`

- [ ] **Step 7: Run tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(inbound-port): rename job domain Input/Output to UseCaseInput/UseCaseOutput"
```

---

### Task 4: Rename inbound port — job_run domain

Rename all Input/Output classes in `application/port/inbound/job_run/`:

| Old | New |
|-----|-----|
| `TriggerJobRunInput` | `TriggerJobRunUseCaseInput` |
| `TriggerJobRunOutput` | `TriggerJobRunUseCaseOutput` |
| `SubmitJobRunInput` (inbound) | `SubmitJobRunUseCaseInput` |
| `SubmitJobRunOutput` | `SubmitJobRunUseCaseOutput` |
| `GetJobRunInput` | `GetJobRunUseCaseInput` |
| `GetJobRunOutput` | `GetJobRunUseCaseOutput` |
| `ListJobRunsInput` | `ListJobRunsUseCaseInput` |
| `ListJobRunsOutput` | `ListJobRunsUseCaseOutput` |
| `ListJobRunsOutputItem` | `ListJobRunsUseCaseOutputItem` |
| `CompleteJobRunInput` | `CompleteJobRunUseCaseInput` |
| `CompleteJobRunOutput` | `CompleteJobRunUseCaseOutput` |
| `FailJobRunInput` | `FailJobRunUseCaseInput` |
| `FailJobRunOutput` | `FailJobRunUseCaseOutput` |

**Files:**
- Modify: All `input.py`, `output.py`, `__init__.py`, `use_case.py` under `application/port/inbound/job_run/` (6 use case dirs × 4 files = ~24 files)
- Modify: `application/port/inbound/job_run/__init__.py`
- Modify: `application/port/inbound/__init__.py`
- Modify: `application/service/job_run/trigger_job_run.py`
- Modify: `application/service/job_run/submit_job_run.py`
- Modify: `application/service/job_run/list_job_runs.py`
- Modify: `application/service/job_run/complete_job_run.py`
- Modify: `application/service/job_run/fail_job_run.py`
- Modify: `application/service/handler/job_run_created_handler.py`
- Modify: `adapter/inbound/web/job_run/trigger_job_run.py`
- Modify: `adapter/inbound/web/job_run/get_job_run.py`
- Modify: `adapter/inbound/web/job_run/list_job_runs.py`
- Modify: `tests/adapter/inbound/web/job_run/test_trigger_job_run.py`
- Modify: `tests/adapter/inbound/web/job_run/test_get_job_run.py`
- Modify: `tests/adapter/inbound/web/job_run/test_list_job_runs.py`
- Modify: `tests/application/service/job_run/test_trigger_job_run.py`
- Modify: `tests/application/service/job_run/test_submit_job_run.py`
- Modify: `tests/application/service/job_run/test_complete_job_run.py`
- Modify: `tests/application/service/job_run/test_fail_job_run.py` (if exists)
- Modify: `tests/application/service/handler/test_job_run_created_handler.py`
- Modify: `tests/test_event_chain_publish.py`

**Important:** The inbound `SubmitJobRunInput` is distinct from the outbound `SubmitJobRunGatewayInput` (renamed in Task 1). After this task, the names are fully unambiguous.

- [ ] **Step 1: Rename class definitions**

For each use case directory under `application/port/inbound/job_run/`, rename classes in `input.py` and `output.py`. Follow the same pattern as Task 3 Step 1.

- [ ] **Step 2: Update use case interfaces**

Update `use_case.py` type annotations in all 6 use case directories.

- [ ] **Step 3: Update re-exports**

Update `__init__.py` at three levels:
1. Each use case's `__init__.py`
2. `application/port/inbound/job_run/__init__.py`
3. `application/port/inbound/__init__.py`

- [ ] **Step 4: Update service implementations**

Update imports and type annotations in:
- `application/service/job_run/trigger_job_run.py`
- `application/service/job_run/submit_job_run.py` (note: this file imports BOTH inbound `SubmitJobRunUseCaseInput` and outbound `SubmitJobRunGatewayInput` — ensure they are correctly distinguished)
- `application/service/job_run/list_job_runs.py`
- `application/service/job_run/complete_job_run.py`
- `application/service/job_run/fail_job_run.py`
- `application/service/handler/job_run_created_handler.py` (uses `SubmitJobRunInput` from inbound → `SubmitJobRunUseCaseInput`)

- [ ] **Step 5: Update web adapter routes**

Update imports in:
- `adapter/inbound/web/job_run/trigger_job_run.py`
- `adapter/inbound/web/job_run/get_job_run.py`
- `adapter/inbound/web/job_run/list_job_runs.py`

- [ ] **Step 6: Update test files**

Update imports and references in:
- `tests/adapter/inbound/web/job_run/test_trigger_job_run.py`
- `tests/adapter/inbound/web/job_run/test_get_job_run.py`
- `tests/adapter/inbound/web/job_run/test_list_job_runs.py`
- `tests/application/service/job_run/test_trigger_job_run.py`
- `tests/application/service/job_run/test_submit_job_run.py`
- `tests/application/service/job_run/test_complete_job_run.py`
- `tests/application/service/job_run/test_fail_job_run.py` (if exists)
- `tests/application/service/handler/test_job_run_created_handler.py`
- `tests/test_event_chain_publish.py`

- [ ] **Step 7: Run tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(inbound-port): rename job_run domain Input/Output to UseCaseInput/UseCaseOutput"
```

---

### Task 5: Rename inbound port — catalog domain

Rename all Input/Output classes in `application/port/inbound/catalog/`:

| Old | New |
|-----|-----|
| `GetTableInput` | `GetTableUseCaseInput` |
| `GetTableOutput` | `GetTableUseCaseOutput` |
| `GetTableSchemaOutput` | `GetTableSchemaUseCaseOutput` |
| `GetTableSchemaFieldOutput` | `GetTableSchemaFieldUseCaseOutput` |
| `ListTablesInput` | `ListTablesUseCaseInput` |
| `ListTablesOutput` | `ListTablesUseCaseOutput` |
| `ListBranchesInput` | `ListBranchesUseCaseInput` |
| `ListBranchesOutput` | `ListBranchesUseCaseOutput` |
| `ListBranchesOutputItem` | `ListBranchesUseCaseOutputItem` |
| `ListTagsInput` | `ListTagsUseCaseInput` |
| `ListTagsOutput` | `ListTagsUseCaseOutput` |
| `ListTagsOutputItem` | `ListTagsUseCaseOutputItem` |
| `ListNamespacesInput` | `ListNamespacesUseCaseInput` |
| `ListNamespacesOutput` | `ListNamespacesUseCaseOutput` |
| `ListSnapshotsInput` | `ListSnapshotsUseCaseInput` |
| `ListSnapshotsOutput` | `ListSnapshotsUseCaseOutput` |
| `ListSnapshotsOutputItem` | `ListSnapshotsUseCaseOutputItem` |

**Files:**
- Modify: All `input.py`, `output.py`, `__init__.py`, `use_case.py` under `application/port/inbound/catalog/` (6 use case dirs)
- Modify: `application/port/inbound/catalog/__init__.py`
- Modify: `application/port/inbound/__init__.py`
- Modify: `application/service/catalog/get_table.py`
- Modify: `application/service/catalog/list_tables.py`
- Modify: `application/service/catalog/list_branches.py`
- Modify: `application/service/catalog/list_tags.py`
- Modify: `application/service/catalog/list_namespaces.py`
- Modify: `application/service/catalog/list_snapshots.py`
- Modify: `adapter/inbound/web/catalog/` route files
- Modify: `tests/adapter/inbound/web/catalog/` test files

- [ ] **Step 1: Rename class definitions**

Same pattern as previous tasks. Note `get_table/output.py` has three classes — rename all three.

- [ ] **Step 2: Update use case interfaces**

Update `use_case.py` type annotations in all 6 use case directories.

- [ ] **Step 3: Update re-exports**

Update `__init__.py` at three levels:
1. Each use case's `__init__.py`
2. `application/port/inbound/catalog/__init__.py`
3. `application/port/inbound/__init__.py`

- [ ] **Step 4: Update service implementations**

Update imports and type annotations in all catalog service files.

- [ ] **Step 5: Update web adapter routes and tests**

Update imports in web adapter route files and their corresponding test files under `tests/adapter/inbound/web/catalog/`.

- [ ] **Step 6: Run tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(inbound-port): rename catalog domain Input/Output to UseCaseInput/UseCaseOutput"
```

---

### Task 6: Rename inbound port — scheduling and outbox domains

| Old | New |
|-----|-----|
| `ScheduleJobsResult` | `ScheduleJobsUseCaseOutput` |
| `PublishEventsResult` | `PublishEventsUseCaseOutput` |

**Files:**
- Modify: `application/port/inbound/scheduling/schedule_jobs/output.py`
- Modify: `application/port/inbound/scheduling/schedule_jobs/__init__.py`
- Modify: `application/port/inbound/scheduling/schedule_jobs/use_case.py`
- Modify: `application/service/scheduling/schedule_jobs.py`
- Modify: `tests/adapter/inbound/scheduler/test_scheduler_loop.py`
- Modify: `application/port/inbound/outbox/publish_events/output.py`
- Modify: `application/port/inbound/outbox/publish_events/__init__.py`
- Modify: `application/port/inbound/outbox/publish_events/use_case.py`
- Modify: `application/service/outbox/publish_events.py`

- [ ] **Step 1: Rename `ScheduleJobsResult` → `ScheduleJobsUseCaseOutput`**

In `application/port/inbound/scheduling/schedule_jobs/output.py`:
```python
@dataclass(frozen=True)
class ScheduleJobsUseCaseOutput:
    """Output returned after one scheduling tick."""

    triggered_count: int = 0
    job_ids: list[str] = field(default_factory=list)
```

- [ ] **Step 2: Update scheduling re-exports and use case**

Update `__init__.py` and `use_case.py` in `scheduling/schedule_jobs/`.

- [ ] **Step 3: Update scheduling service and test**

Update imports in:
- `application/service/scheduling/schedule_jobs.py`
- `tests/adapter/inbound/scheduler/test_scheduler_loop.py`

- [ ] **Step 4: Rename `PublishEventsResult` → `PublishEventsUseCaseOutput`**

In `application/port/inbound/outbox/publish_events/output.py`:
```python
@dataclass(frozen=True)
class PublishEventsUseCaseOutput:
    """Output of one outbox publishing tick."""

    published_count: int
```

- [ ] **Step 5: Update outbox re-exports, use case, and service**

Update `__init__.py`, `use_case.py`, and `application/service/outbox/publish_events.py`.

- [ ] **Step 6: Run tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(inbound-port): rename scheduling/outbox Result to UseCaseOutput"
```

---

### Task 7: Write architecture test for DTO naming conventions

**Files:**
- Create: `tests/architecture/test_dto_naming.py`

- [ ] **Step 1: Write the architecture test**

Create `tests/architecture/test_dto_naming.py`:

```python
"""Guard DTO naming conventions across layers.

Rules enforced:
1. Inbound port input.py classes must end with 'UseCaseInput'
2. Inbound port output.py classes must end with 'UseCaseOutput' or 'UseCaseOutputItem'
3. Outbound port input.py classes must end with 'GatewayInput'
4. Outbound port output.py classes must end with 'GatewayOutput'
5. Web adapter dto.py classes must end with 'ApiRequest' or 'ApiResponse'
6. Class name prefix must start with PascalCase of parent directory name
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[2]
_INBOUND_PORT = _BACKEND / "application" / "port" / "inbound"
_OUTBOUND_PORT = _BACKEND / "application" / "port" / "outbound"
_WEB_ADAPTER = _BACKEND / "adapter" / "inbound" / "web"


def _to_pascal(snake: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake.split("_"))


def _defined_classes(file_path: Path) -> list[str]:
    """Return class names defined in a Python file."""
    source = file_path.read_text()
    tree = ast.parse(source)
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    ]


def _collect_port_files(
    root: Path,
    filename: str,
) -> list[tuple[str, Path]]:
    """Find all input.py or output.py files under port directories.

    Returns (use_case_dir_name, file_path) tuples.
    """
    results: list[tuple[str, Path]] = []
    for f in sorted(root.rglob(filename)):
        if f.name == "__init__.py":
            continue
        use_case_dir = f.parent.name
        results.append((use_case_dir, f))
    return results


def _collect_dto_files(root: Path) -> list[tuple[str, Path]]:
    """Find all dto.py files under web adapter directories.

    Returns (domain_dir_name, file_path) tuples.
    """
    results: list[tuple[str, Path]] = []
    for f in sorted(root.rglob("dto.py")):
        results.append((f.parent.name, f))
    return results


def _port_id(entry: tuple[str, Path]) -> str:
    dir_name, file_path = entry
    layer = "inbound" if "inbound" in str(file_path) else "outbound"
    return f"{layer}/{dir_name}/{file_path.name}"


def _dto_id(entry: tuple[str, Path]) -> str:
    dir_name, _ = entry
    return f"web/{dir_name}/dto.py"


# --- Rule 1 & 2: Inbound port input/output naming ---

_INBOUND_INPUT_FILES = _collect_port_files(_INBOUND_PORT, "input.py")
_INBOUND_OUTPUT_FILES = _collect_port_files(_INBOUND_PORT, "output.py")


@pytest.mark.parametrize("entry", _INBOUND_INPUT_FILES, ids=_port_id)
def test_inbound_input_suffix(entry: tuple[str, Path]) -> None:
    dir_name, file_path = entry
    prefix = _to_pascal(dir_name)
    for cls in _defined_classes(file_path):
        assert cls.endswith("UseCaseInput"), (
            f"{cls} in {file_path.name} must end with 'UseCaseInput'"
        )
        assert cls.startswith(prefix), (
            f"{cls} must start with '{prefix}' (from dir '{dir_name}')"
        )


@pytest.mark.parametrize("entry", _INBOUND_OUTPUT_FILES, ids=_port_id)
def test_inbound_output_suffix(entry: tuple[str, Path]) -> None:
    dir_name, file_path = entry
    prefix = _to_pascal(dir_name)
    allowed_suffixes = ("UseCaseOutput", "UseCaseOutputItem")
    for cls in _defined_classes(file_path):
        assert cls.startswith(prefix), (
            f"{cls} must start with '{prefix}' (from dir '{dir_name}')"
        )
        assert any(cls.endswith(s) for s in allowed_suffixes), (
            f"{cls} in {file_path.name} must end with one of {allowed_suffixes}"
        )


# --- Rule 3 & 4: Outbound port input/output naming ---

_OUTBOUND_INPUT_FILES = _collect_port_files(_OUTBOUND_PORT, "input.py")
_OUTBOUND_OUTPUT_FILES = _collect_port_files(_OUTBOUND_PORT, "output.py")


@pytest.mark.parametrize("entry", _OUTBOUND_INPUT_FILES, ids=_port_id)
def test_outbound_input_suffix(entry: tuple[str, Path]) -> None:
    dir_name, file_path = entry
    prefix = _to_pascal(dir_name)
    for cls in _defined_classes(file_path):
        assert cls.endswith("GatewayInput"), (
            f"{cls} in {file_path.name} must end with 'GatewayInput'"
        )
        assert cls.startswith(prefix), (
            f"{cls} must start with '{prefix}' (from dir '{dir_name}')"
        )


@pytest.mark.parametrize("entry", _OUTBOUND_OUTPUT_FILES, ids=_port_id)
def test_outbound_output_suffix(entry: tuple[str, Path]) -> None:
    dir_name, file_path = entry
    prefix = _to_pascal(dir_name)
    for cls in _defined_classes(file_path):
        assert cls.endswith("GatewayOutput"), (
            f"{cls} in {file_path.name} must end with 'GatewayOutput'"
        )
        assert cls.startswith(prefix), (
            f"{cls} must start with '{prefix}' (from dir '{dir_name}')"
        )


# --- Rule 5: Web adapter dto naming ---

_DTO_FILES = _collect_dto_files(_WEB_ADAPTER)


@pytest.mark.parametrize("entry", _DTO_FILES, ids=_dto_id)
def test_web_dto_suffix(entry: tuple[str, Path]) -> None:
    _, file_path = entry
    allowed_suffixes = ("ApiRequest", "ApiResponse")
    for cls in _defined_classes(file_path):
        assert any(cls.endswith(s) for s in allowed_suffixes), (
            f"{cls} in {file_path.name} must end with one of {allowed_suffixes}"
        )
```

- [ ] **Step 2: Run architecture test**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/architecture/test_dto_naming.py -v`
Expected: All tests PASS (all renames completed in previous tasks).

- [ ] **Step 3: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/architecture/test_dto_naming.py
git commit -m "test(arch): add architecture test for DTO naming conventions"
```

---

### Task 8: Update CLAUDE.md with naming convention

**Files:**
- Modify: `/Users/kcl/Projects/retail-lakehouse/CLAUDE.md`

- [ ] **Step 1: Add naming convention to CLAUDE.md**

Add a new section after the "Outbound Port & Adapter Naming Convention" section:

```markdown
## Inbound Port & Web Adapter DTO Naming Convention

Layer-specific suffixes make each class's origin immediately identifiable:

| Layer | File | Required Suffix | Example |
|-------|------|----------------|---------|
| Inbound port | `input.py` | `UseCaseInput` | `CreateJobUseCaseInput` |
| Inbound port | `output.py` | `UseCaseOutput` / `UseCaseOutputItem` | `CreateJobUseCaseOutput` |
| Outbound port | `input.py` | `GatewayInput` | `SubmitJobRunGatewayInput` |
| Outbound port | `output.py` | `GatewayOutput` | `ReadCatalogGatewayOutput` |
| Web adapter | `dto.py` | `ApiRequest` / `ApiResponse` | `CreateJobApiRequest` |

**Prefix rule (port layers only):** Class name must start with the PascalCase form of its parent directory name. Web adapter DTOs only require the suffix; verb prefix is convention, not enforced.

Enforced by `tests/architecture/test_dto_naming.py`.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add DTO naming convention to CLAUDE.md"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS.

- [ ] **Step 2: Run linter checks**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check .`
Expected: No errors.

- [ ] **Step 3: Run type checker**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ty check`
Expected: No errors.

- [ ] **Step 4: Run import linter**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`
Expected: No contract violations.

- [ ] **Step 5: Run architecture tests specifically**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/architecture/ -v`
Expected: All architecture tests PASS.
