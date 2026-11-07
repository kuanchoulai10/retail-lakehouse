# Project Guidelines

## Language

Respond in the same language as the user's message. The user typically communicates in Traditional Chinese (繁體中文) or English.

## Shell Commands

- Never use `cd` to change directory. Always use absolute paths or tool flags like `--directory`, `--project`.
- Use `uv run` instead of bare `python`, `python3`, `pytest`, or `pip`. Example: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
- The local minikube/dev cluster context is `retail-lakehouse`. Infra scripts (`*/bootstrap.sh`, `*/validate.sh`, `*/patch.sh`) require `KUBE_CONTEXT` to be set explicitly — there is no fallback (scripts fail fast with `KUBE_CONTEXT is required`). Always pass it when invoking Taskfile entries or running scripts directly, e.g. `task onboard KUBE_CONTEXT=retail-lakehouse`.

## Project Overview

**What it is:** an Iceberg lakehouse platform on minikube plus a self-built Table Maintenance service (`src/table-maintenance`, DDD + Clean Architecture) that schedules Iceberg maintenance (compaction, snapshot expiry). Long-term vision: "GitHub for Data", a DataOps platform.

**Data flow:** MySQL →(Debezium CDC)→ Kafka →(Iceberg Sink)→ Iceberg on RustFS, catalog = Polaris → queried by Trino. Polaris catalog events →(Kafka event listener)→ Kafka topic `polaris-catalog-events` (key = event UUID, value = JSON; read it with `kafka-console-consumer.sh` in a broker pod or Kafka UI). Table maintenance Spark event logs → RustFS bucket `spark-event-logs` (zstd, rolling 128m, `logStageExecutorMetrics`, 3-day expiry) → on completion RustFS sends one `s3:ObjectCreated:Copy` event (the `appstatus_<appId>.inprogress` → `appstatus_<appId>` rename, prefix `eventlog_v2_`) → Kafka topic `spark-event-log-completions` (for a future metrics-analysis runtime).

## Where the rest lives

Topic files load on demand: a nested `CLAUDE.md` is read when you work on files under its directory, and the `docs/agents/` files are read when needed.

| Topic | File |
|---|---|
| Waves, cluster runtime, deployed components, ambient mesh, Kubernetes label rules | `platform/CLAUDE.md` |
| Backend layering, aggregate axis, DDD base types, port / adapter and DTO naming | `src/table-maintenance/backend/CLAUDE.md` |
| Console UI rules | `src/console/CLAUDE.md` |
| History of what landed and finished initiatives | `docs/agents/project-history.md` |
| Known follow-ups and deferred work | `docs/agents/known-follow-ups.md` |
| Architecture decisions | `docs/adr/` |

Keep this file to rules that apply everywhere; put topic rules in the topic file. When work lands, add a line to `docs/agents/project-history.md` and update the topic file it changes.

## On hold

Do not touch unless the user re-opens them: `platform/30-thanos`, `platform/24-e2e-validation`, and the ArgoCD path (`platform/00-argocd`, `01-argocd-health-checks`, `02-argocd-apps`, `charts/app-of-apps`).

## Code Style

- **One object per file.** Each Python file exports one primary class, enum, or function. If a file grows to contain multiple exported objects, split it.
- **Descriptive filenames.** Name files after their primary export: `create_job.py` not `create.py`, `job_status.py` not `status.py`.
- **Package re-exports via `__init__.py`.** Expose a clean public API at the package level so consumers use `from models import JobRequest` instead of `from models.job_request import JobRequest`.
- **Intra-package: direct imports.** Within the same package, import from the module directly (e.g., `from models.job_status import JobStatus`) to avoid circular imports.
- **ABC over Protocol** for interface definitions. Use `abc.ABC` with `@abstractmethod`, not `typing.Protocol`.
- **StrEnum** for string-valued enumerations.
- **`from __future__ import annotations`** in every module for deferred type evaluation.

## Architecture Mindset

- **DDD best practices first.** Always prefer Domain-Driven Design idioms and patterns. When in doubt, choose the approach closest to established DDD literature (Evans, Vernon).
- **Design for high complexity.** This project will grow significantly in complexity. Favor extensible, well-structured designs over minimal implementations. Over-engineering is acceptable — under-engineering is not.

## Development Workflow

- **TDD always.** Write the failing test first, watch it fail, write minimal code to pass, then refactor. No exceptions.
- **Verify before commit.** Every commit must pass: `pytest -v`, `ty check`, `ruff check .`, `lint-imports`.
- **Semantic commits.** Use conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `docs(scope):`.
- **Incremental, atomic commits.** Each commit is independently valid — tests pass, linter clean.
- **Taskfile for automation.** `task pre-pr` runs all checks (pre-commit + unit-test + arch-test).

## Project Vision

This is being built as one data platform; multi-tenancy is not a goal (dropped 2026-11-06). The current bounded context is table maintenance (aggregates `Table`, `TableMaintenancePreset`, `TableDiscoveryRule`, `TableDiscoverySettings`, `TableMaintenanceRun`); a catalog context (catalogs, namespaces, tables, views, with Polaris as the source of truth) and an access context (principals, principal roles, catalog roles and their grants) are planned next. Design decisions should consider future extensibility across bounded contexts.

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, default strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

`docs/adr/` at the repo root. See `docs/agents/domain.md`.
