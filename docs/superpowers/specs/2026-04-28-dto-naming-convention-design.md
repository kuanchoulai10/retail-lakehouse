# DTO Naming Convention Design Spec

## Problem

Classes across layers use similar naming patterns (`CreateJobInput` vs `SubmitJobRunInput`), making it hard to tell at a glance which layer a class belongs to. There is no architectural enforcement to prevent naming drift.

## Decision

Introduce layer-specific suffixes and prefix rules for all DTO classes, enforced by architecture tests.

## Naming Rules

### Inbound Port (Use Case Layer)

| File | Suffix | Example |
|------|--------|---------|
| `input.py` | `UseCaseInput` | `CreateJobUseCaseInput` |
| `output.py` | `UseCaseOutput` | `CreateJobUseCaseOutput` |

**Prefix**: Must match the PascalCase form of the parent directory name.
- Directory `create_job/` → prefix `CreateJob`
- Directory `trigger_job_run/` → prefix `TriggerJobRun`

### Outbound Port (Gateway Layer)

| File | Suffix | Example |
|------|--------|---------|
| `input.py` | `GatewayInput` | `SubmitJobRunGatewayInput` |
| `output.py` | `GatewayOutput` | `ReadCatalogGatewayOutput` |

**Prefix**: Must match the PascalCase form of the parent directory name.
- Directory `submit_job_run/` → prefix `SubmitJobRun`

### Web Adapter (API Layer)

| File | Suffix | Example |
|------|--------|---------|
| `dto.py` | `ApiRequest` / `ApiResponse` | `CreateJobApiRequest`, `GetJobApiResponse` |

**Prefix**: Must be `{Verb}{Noun}` in PascalCase. Every DTO must have a verb prefix (no bare `JobApiRequest`).

## What Changes

### Renames

| Layer | Before | After |
|-------|--------|-------|
| Inbound port | `CreateJobInput` | `CreateJobUseCaseInput` |
| Inbound port | `CreateJobOutput` | `CreateJobUseCaseOutput` |
| Inbound port | `GetJobInput` | `GetJobUseCaseInput` |
| Inbound port | `GetJobOutput` | `GetJobUseCaseOutput` |
| Inbound port | `UpdateJobInput` | `UpdateJobUseCaseInput` |
| Inbound port | `UpdateJobOutput` | `UpdateJobUseCaseOutput` |
| Inbound port | `DeleteJobInput` | `DeleteJobUseCaseInput` |
| Inbound port | `DeleteJobOutput` | `DeleteJobUseCaseOutput` |
| Inbound port | `ListJobsInput` | `ListJobsUseCaseInput` |
| Inbound port | `ListJobsOutput` | `ListJobsUseCaseOutput` |
| Inbound port | `TriggerJobRunInput` | `TriggerJobRunUseCaseInput` |
| Inbound port | `TriggerJobRunOutput` | `TriggerJobRunUseCaseOutput` |
| Inbound port | `SubmitJobRunInput` (inbound) | `SubmitJobRunUseCaseInput` |
| Inbound port | `SubmitJobRunOutput` | `SubmitJobRunUseCaseOutput` |
| Inbound port | `GetJobRunInput` | `GetJobRunUseCaseInput` |
| Inbound port | `GetJobRunOutput` | `GetJobRunUseCaseOutput` |
| Inbound port | `ListJobRunsInput` | `ListJobRunsUseCaseInput` |
| Inbound port | `ListJobRunsOutput` | `ListJobRunsUseCaseOutput` |
| Inbound port | `CompleteJobRunInput` | `CompleteJobRunUseCaseInput` |
| Inbound port | `CompleteJobRunOutput` | `CompleteJobRunUseCaseOutput` |
| Inbound port | `FailJobRunInput` | `FailJobRunUseCaseInput` |
| Inbound port | `FailJobRunOutput` | `FailJobRunUseCaseOutput` |
| Inbound port | `ListNamespacesInput` | `ListNamespacesUseCaseInput` |
| Inbound port | `ListNamespacesOutput` | `ListNamespacesUseCaseOutput` |
| Inbound port | `ListTablesInput` | `ListTablesUseCaseInput` |
| Inbound port | `ListTablesOutput` | `ListTablesUseCaseOutput` |
| Inbound port | `ListBranchesInput` | `ListBranchesUseCaseInput` |
| Inbound port | `ListBranchesOutput` | `ListBranchesUseCaseOutput` |
| Inbound port | `ListTagsInput` | `ListTagsUseCaseInput` |
| Inbound port | `ListTagsOutput` | `ListTagsUseCaseOutput` |
| Inbound port | `ListSnapshotsInput` | `ListSnapshotsUseCaseInput` |
| Inbound port | `ListSnapshotsOutput` | `ListSnapshotsUseCaseOutput` |
| Inbound port | `GetTableInput` | `GetTableUseCaseInput` |
| Inbound port | `GetTableOutput` | `GetTableUseCaseOutput` |
| Inbound port | `ScheduleJobsOutput` | `ScheduleJobsUseCaseOutput` |
| Inbound port | `PublishEventsOutput` | `PublishEventsUseCaseOutput` |
| Outbound port | `SubmitJobRunInput` (outbound) | `SubmitJobRunGatewayInput` |
| Web adapter | `JobApiRequest` | `CreateJobApiRequest` |

### Not Changed

- File names (`input.py`, `output.py`, `dto.py`) remain the same
- Directory structure remains the same
- Gateway class names (e.g., `SubmitJobRunGateway`) remain the same
- UseCase class names (e.g., `CreateJob`) remain the same
- All references (services, adapters, tests, `__init__.py` re-exports) must be updated to match

## Architecture Test

A new test `tests/architecture/test_dto_naming.py` will enforce:

1. **Inbound port input/output files**: Every class defined in `application/port/inbound/**/input.py` must end with `UseCaseInput`. Every class in `output.py` must end with `UseCaseOutput`.
2. **Outbound port input/output files**: Every class defined in `application/port/outbound/**/input.py` must end with `GatewayInput`. Every class in `output.py` must end with `GatewayOutput`.
3. **Web adapter dto files**: Every class defined in `adapter/inbound/web/**/dto.py` must end with `ApiRequest` or `ApiResponse`.
4. **Prefix rule**: The class name prefix (everything before the suffix) must match the PascalCase conversion of the parent directory name. For web adapter DTOs, the prefix must start with a known verb.

The test discovers files via glob, parses class names via AST, and validates against the rules above.
