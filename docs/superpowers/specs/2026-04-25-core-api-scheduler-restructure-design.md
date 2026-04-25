# Design: Restructure backend/ into core/ + api/ + scheduler/

**Date:** 2026-04-25
**Status:** Approved

## Problem

The table-maintenance system has two deployable processes (API server + scheduler) that share domain logic. The scheduler lives in a separate project (`src/table-maintenance/scheduler/`) and imports backend modules via PYTHONPATH hacks in the Dockerfile. This makes the relationship between the two projects implicit and fragile.

## Decision

Restructure the backend into three top-level Python packages within a single project:

- **`core/`** — shared domain model, application services, ports, outbound adapters, DDD base, configs
- **`api/`** — FastAPI-specific: inbound web adapter, DI dependencies, API main
- **`scheduler/`** — polling loop and scheduler main

Single Docker image. `ROLE` env var (`api` or `scheduler`) selects which process runs via `entrypoint.py`.

## Key Design Choices

1. **`core/` prefix on all shared imports** — explicit namespace, clear what's shared vs. role-specific
2. **Scheduler is NOT an inbound adapter** — it's a self-driving infrastructure component, not externally driven
3. **Single pyproject.toml, single image** — simplifies build/deploy, env var switches role
4. **import-linter enforces boundaries** — `scheduler` cannot import `api` or `fastapi`

## Import Convention

| Package | Contains | Example import |
|---------|----------|---------------|
| `core.base` | DDD shared kernel | `from core.base.entity import Entity` |
| `core.application` | Domain, services, ports | `from core.application.domain.model.job import Job` |
| `core.adapter.outbound` | SQL repos, K8s adapter | `from core.adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo` |
| `core.configs` | AppSettings, enums | `from core.configs import JobsRepoAdapter` |
| `api.adapter.inbound.web` | FastAPI routes | `from api.adapter.inbound.web import router` |
| `api.dependencies` | FastAPI DI | `from api.dependencies.repos import get_jobs_repo` |
| `scheduler` | Polling loop | `from scheduler.scheduler_loop import SchedulerLoop` |
