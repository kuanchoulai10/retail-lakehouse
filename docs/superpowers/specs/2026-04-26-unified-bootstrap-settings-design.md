# Unified Bootstrap Settings Design

**Date:** 2026-04-26
**Status:** Approved

## Problem

The bootstrap layer has three inconsistent parameter collection patterns:

1. `bootstrap/api.py` uses `AppSettings` (pydantic-settings) with `BACKEND_` prefix
2. `bootstrap/scheduler.py` uses bare `os.environ.get("SCHEDULER_DATABASE_URL")` and `os.environ.get("SCHEDULER_INTERVAL_SECONDS")`
3. `bootstrap/messaging.py` uses bare `os.environ.get("OUTBOX_DATABASE_URL")` and `os.environ.get("OUTBOX_INTERVAL_SECONDS")`
4. `entrypoint.py` uses bare `os.environ.get("ROLE")` to dispatch components

This means no single source of truth for configuration, no validation, and inconsistent env var naming.

## Design

Unify all configuration into a single hierarchical `AppSettings` (pydantic-settings) with `GLAC_` prefix (Glacier — the source of icebergs, matching the Iceberg table format this platform manages).

### Decisions Made

- **Env prefix:** `GLAC_` (Glacier metaphor for Iceberg)
- **Database:** All components share one database configuration (no per-component overrides)
- **Component naming:** `api`, `scheduler`, `messaging` — matching `bootstrap/*.py` filenames
- **Settings loading:** Single `AppSettings` loads all component settings regardless of active component
- **ROLE → COMPONENT:** Rename env var from `ROLE` to `GLAC_COMPONENT`

### Settings Hierarchy

```python
class Component(StrEnum):
    API = "api"
    SCHEDULER = "scheduler"
    MESSAGING = "messaging"

class SchedulerSettings(BaseModel):
    interval_seconds: int = 30

class MessagingSettings(BaseModel):
    interval_seconds: int = 5

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GLAC_",
        env_nested_delimiter="__",
    )

    component: Component = Component.API

    # Database (shared by all components)
    database_backend: DatabaseBackend = DatabaseBackend.SQLITE
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    sqlite: SqliteSettings = Field(default_factory=SqliteSettings)

    # Adapter selection
    jobs_repo_adapter: JobsRepoAdapter = JobsRepoAdapter.IN_MEMORY
    job_runs_repo_adapter: JobRunsRepoAdapter = JobRunsRepoAdapter.IN_MEMORY
    job_run_executor_adapter: JobRunExecutorAdapter = JobRunExecutorAdapter.IN_MEMORY

    # Infrastructure
    k8s: K8sSettings = Field(default_factory=K8sSettings)
    iceberg_catalog_uri: str = "http://polaris:8181/api/catalog"
    iceberg_catalog_name: str = "iceberg"
    iceberg_catalog_credential: str = ""
    iceberg_catalog_warehouse: str = ""
    iceberg_catalog_scope: str = ""

    # Component-specific
    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    messaging: MessagingSettings = Field(default_factory=MessagingSettings)
```

### Environment Variable Examples

```bash
# Component selection
GLAC_COMPONENT=scheduler

# Shared database
GLAC_DATABASE_BACKEND=postgres
GLAC_POSTGRES__DB_URL=postgresql://user:pass@host:5432/db

# Component-specific (nested via __)
GLAC_SCHEDULER__INTERVAL_SECONDS=60
GLAC_MESSAGING__INTERVAL_SECONDS=10

# Adapter selection
GLAC_JOBS_REPO_ADAPTER=sql
GLAC_K8S__CONTEXT=minikube
```

### entrypoint.py

Replace `os.environ.get("ROLE")` with `settings.component`:

```python
def main() -> None:
    settings = get_settings()
    match settings.component:
        case Component.API:
            import uvicorn
            uvicorn.run("bootstrap.api:app", host="0.0.0.0", port=8000)
        case Component.SCHEDULER:
            from bootstrap.scheduler import main as scheduler_main
            scheduler_main()
        case Component.MESSAGING:
            from bootstrap.messaging import main as messaging_main
            messaging_main()
```

### bootstrap/scheduler.py and messaging.py

Replace bare `os.environ.get()` with `get_settings()`:

```python
# scheduler.py
def build_scheduler() -> SchedulerLoop:
    settings = get_settings()
    engine = build_engine(settings)
    metadata.create_all(engine)
    # ... use settings.scheduler.interval_seconds
```

```python
# messaging.py
def build_publisher() -> PublisherLoop:
    settings = get_settings()
    engine = build_engine(settings)
    metadata.create_all(engine)
    # ... use settings.messaging.interval_seconds
```

## Files Changed

| File | Change |
|---|---|
| `bootstrap/configs/app.py` | Add `component`, `scheduler`, `messaging` fields; change prefix to `GLAC_` |
| `bootstrap/configs/component.py` | New: `Component` StrEnum |
| `bootstrap/configs/scheduler_settings.py` | New: `SchedulerSettings` BaseModel |
| `bootstrap/configs/messaging_settings.py` | New: `MessagingSettings` BaseModel |
| `bootstrap/configs/__init__.py` | Re-export new types |
| `entrypoint.py` | Use `settings.component` instead of `os.environ.get("ROLE")` |
| `bootstrap/scheduler.py` | Use `get_settings()` + `build_engine()` instead of `os.environ.get()` |
| `bootstrap/messaging.py` | Use `get_settings()` + `build_engine()` instead of `os.environ.get()` |
| All tests using `BACKEND_` env vars | Change to `GLAC_` prefix |
| `CLAUDE.md` | Update env var references |

## Not in Scope

- Per-component database overrides (can be added later if needed)
- API-specific settings (host, port) — currently hardcoded in uvicorn call, can be extracted later
- Logging configuration unification
