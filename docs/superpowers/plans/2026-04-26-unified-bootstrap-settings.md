# Unified Bootstrap Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify all bootstrap configuration into a single hierarchical `AppSettings` with `GLAC_` prefix, replacing scattered `os.environ.get()` calls and renaming `ROLE` to `COMPONENT`.

**Architecture:** Add `Component` StrEnum + `SchedulerSettings`/`MessagingSettings` sub-models to `AppSettings`. Update `entrypoint.py` to use `settings.component`. Refactor `bootstrap/scheduler.py` and `bootstrap/messaging.py` to use `get_settings()` instead of `os.environ.get()`. Update all tests from `BACKEND_` to `GLAC_` prefix.

**Tech Stack:** Python, pydantic-settings, pytest

**Working directory:** `src/table-maintenance/backend` (all paths relative to this unless noted)

**Commands:** All commands use `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend` prefix. Abbreviated as `UV_RUN` in this plan.

---

### Task 1: Add Component StrEnum

**Files:**
- Create: `bootstrap/configs/component.py`
- Test: `tests/bootstrap/configs/test_component.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for Component enum."""

from __future__ import annotations

from bootstrap.configs.component import Component


def test_component_values():
    """Verify all component values match bootstrap filenames."""
    assert Component.API == "api"
    assert Component.SCHEDULER == "scheduler"
    assert Component.MESSAGING == "messaging"


def test_component_is_str_enum():
    """Verify Component is a StrEnum."""
    assert isinstance(Component.API, str)
    assert Component.API == "api"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_RUN pytest tests/bootstrap/configs/test_component.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementation**

```python
"""Component enumeration for entry point dispatch."""

from __future__ import annotations

from enum import StrEnum


class Component(StrEnum):
    """Identifies which application component to run."""

    API = "api"
    SCHEDULER = "scheduler"
    MESSAGING = "messaging"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `UV_RUN pytest tests/bootstrap/configs/test_component.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bootstrap/configs/component.py tests/bootstrap/configs/test_component.py
git commit -m "feat(config): add Component StrEnum for entry point dispatch"
```

---

### Task 2: Add SchedulerSettings and MessagingSettings sub-models

**Files:**
- Create: `bootstrap/configs/scheduler_settings.py`
- Create: `bootstrap/configs/messaging_settings.py`
- Test: `tests/bootstrap/configs/test_scheduler_settings.py`
- Test: `tests/bootstrap/configs/test_messaging_settings.py`

- [ ] **Step 1: Write the failing tests**

`tests/bootstrap/configs/test_scheduler_settings.py`:
```python
"""Tests for SchedulerSettings."""

from __future__ import annotations

from bootstrap.configs.scheduler_settings import SchedulerSettings


def test_default_interval():
    """Verify default interval is 30 seconds."""
    settings = SchedulerSettings()
    assert settings.interval_seconds == 30


def test_custom_interval():
    """Verify interval can be overridden."""
    settings = SchedulerSettings(interval_seconds=60)
    assert settings.interval_seconds == 60
```

`tests/bootstrap/configs/test_messaging_settings.py`:
```python
"""Tests for MessagingSettings."""

from __future__ import annotations

from bootstrap.configs.messaging_settings import MessagingSettings


def test_default_interval():
    """Verify default interval is 5 seconds."""
    settings = MessagingSettings()
    assert settings.interval_seconds == 5


def test_custom_interval():
    """Verify interval can be overridden."""
    settings = MessagingSettings(interval_seconds=10)
    assert settings.interval_seconds == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `UV_RUN pytest tests/bootstrap/configs/test_scheduler_settings.py tests/bootstrap/configs/test_messaging_settings.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Write minimal implementations**

`bootstrap/configs/scheduler_settings.py`:
```python
"""Scheduler-specific configuration."""

from __future__ import annotations

from pydantic import BaseModel


class SchedulerSettings(BaseModel):
    """Settings for the scheduler component."""

    interval_seconds: int = 30
```

`bootstrap/configs/messaging_settings.py`:
```python
"""Messaging-specific configuration."""

from __future__ import annotations

from pydantic import BaseModel


class MessagingSettings(BaseModel):
    """Settings for the messaging (outbox publisher) component."""

    interval_seconds: int = 5
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `UV_RUN pytest tests/bootstrap/configs/test_scheduler_settings.py tests/bootstrap/configs/test_messaging_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add bootstrap/configs/scheduler_settings.py bootstrap/configs/messaging_settings.py tests/bootstrap/configs/test_scheduler_settings.py tests/bootstrap/configs/test_messaging_settings.py
git commit -m "feat(config): add SchedulerSettings and MessagingSettings sub-models"
```

---

### Task 3: Update AppSettings — add component, scheduler, messaging fields and change prefix to GLAC_

**Files:**
- Modify: `bootstrap/configs/app.py`
- Modify: `bootstrap/configs/__init__.py`
- Modify: `tests/bootstrap/configs/test_app.py`

- [ ] **Step 1: Write the failing test for new fields**

Add to `tests/bootstrap/configs/test_app.py`:

```python
def test_component_defaults_to_api():
    """Verify component defaults to API."""
    settings = AppSettings()
    assert settings.component == Component.API


def test_component_from_env(monkeypatch):
    """Verify GLAC_COMPONENT env var sets the component."""
    monkeypatch.setenv("GLAC_COMPONENT", "scheduler")
    settings = AppSettings()
    assert settings.component == Component.SCHEDULER


def test_scheduler_settings_nested(monkeypatch):
    """Verify GLAC_SCHEDULER__INTERVAL_SECONDS sets scheduler interval."""
    monkeypatch.setenv("GLAC_SCHEDULER__INTERVAL_SECONDS", "60")
    settings = AppSettings()
    assert settings.scheduler.interval_seconds == 60


def test_messaging_settings_nested(monkeypatch):
    """Verify GLAC_MESSAGING__INTERVAL_SECONDS sets messaging interval."""
    monkeypatch.setenv("GLAC_MESSAGING__INTERVAL_SECONDS", "10")
    settings = AppSettings()
    assert settings.messaging.interval_seconds == 10
```

Also add the import at the top:
```python
from bootstrap.configs.component import Component
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `UV_RUN pytest tests/bootstrap/configs/test_app.py -v`
Expected: FAIL — `AppSettings` doesn't have `component` field yet, and prefix is still `BACKEND_`

- [ ] **Step 3: Update AppSettings**

Modify `bootstrap/configs/app.py` — change `env_prefix` from `"BACKEND_"` to `"GLAC_"`, add `component`, `scheduler`, and `messaging` fields:

```python
"""Define the AppSettings configuration model."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bootstrap.configs.component import Component
from bootstrap.configs.database_backend import DatabaseBackend
from bootstrap.configs.job_run_executor_adapter import JobRunExecutorAdapter
from bootstrap.configs.job_runs_repo_adapter import JobRunsRepoAdapter
from bootstrap.configs.jobs_repo_adapter import JobsRepoAdapter
from bootstrap.configs.k8s_settings import K8sSettings
from bootstrap.configs.messaging_settings import MessagingSettings
from bootstrap.configs.postgres_settings import PostgresSettings
from bootstrap.configs.scheduler_settings import SchedulerSettings
from bootstrap.configs.sqlite_settings import SqliteSettings


class AppSettings(BaseSettings):
    """Root application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GLAC_",
        env_nested_delimiter="__",
    )

    component: Component = Component.API

    jobs_repo_adapter: JobsRepoAdapter = JobsRepoAdapter.IN_MEMORY
    job_runs_repo_adapter: JobRunsRepoAdapter = JobRunsRepoAdapter.IN_MEMORY
    job_run_executor_adapter: JobRunExecutorAdapter = JobRunExecutorAdapter.IN_MEMORY
    database_backend: DatabaseBackend = DatabaseBackend.SQLITE
    k8s: K8sSettings = Field(default_factory=K8sSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    sqlite: SqliteSettings = Field(default_factory=SqliteSettings)
    iceberg_catalog_uri: str = "http://polaris:8181/api/catalog"
    iceberg_catalog_name: str = "iceberg"
    iceberg_catalog_credential: str = ""
    iceberg_catalog_warehouse: str = ""
    iceberg_catalog_scope: str = ""

    scheduler: SchedulerSettings = Field(default_factory=SchedulerSettings)
    messaging: MessagingSettings = Field(default_factory=MessagingSettings)
```

- [ ] **Step 4: Update `bootstrap/configs/__init__.py`** to re-export new types

Add `Component`, `MessagingSettings`, `SchedulerSettings` to imports and `__all__`.

- [ ] **Step 5: Update all existing tests from `BACKEND_` to `GLAC_` prefix**

Run this sed command from the backend directory:

```bash
find tests -path '*/.venv' -prune -o -name '*.py' -print | xargs sed -i '' 's/"BACKEND_/"GLAC_/g'
```

This changes all env var references like `monkeypatch.setenv("BACKEND_K8S__NAMESPACE", ...)` to `monkeypatch.setenv("GLAC_K8S__NAMESPACE", ...)`.

- [ ] **Step 6: Run the full test suite**

Run: `UV_RUN pytest -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat(config): add component/scheduler/messaging to AppSettings, change prefix to GLAC_"
```

---

### Task 4: Update entrypoint.py to use settings.component

**Files:**
- Modify: `entrypoint.py`
- Test: existing tests (verify entrypoint still works)

- [ ] **Step 1: Write the failing test**

Add `tests/test_entrypoint.py`:

```python
"""Tests for entrypoint component dispatch."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bootstrap.configs.component import Component


def test_api_component_calls_uvicorn(monkeypatch):
    """Verify GLAC_COMPONENT=api starts uvicorn."""
    monkeypatch.setenv("GLAC_COMPONENT", "api")
    mock_uvicorn = MagicMock()
    with patch.dict("sys.modules", uvicorn=mock_uvicorn):
        from importlib import reload

        import entrypoint

        reload(entrypoint)
        # Clear settings cache
        from bootstrap.dependencies.settings import get_settings
        get_settings.cache_clear()

        entrypoint.main()
        mock_uvicorn.run.assert_called_once()


def test_invalid_component_exits(monkeypatch):
    """Verify invalid GLAC_COMPONENT raises SystemExit."""
    monkeypatch.setenv("GLAC_COMPONENT", "invalid")
    from bootstrap.dependencies.settings import get_settings
    get_settings.cache_clear()

    with pytest.raises(Exception):
        from importlib import reload
        import entrypoint
        reload(entrypoint)
        entrypoint.main()
```

Note: testing entry points with lazy imports is tricky. A simpler approach is to just verify the entrypoint module loads and the settings are read correctly. The existing integration tests already cover the dispatch behavior indirectly.

- [ ] **Step 2: Update entrypoint.py**

```python
"""Entry point: selects api, scheduler, or messaging component via GLAC_COMPONENT."""

from __future__ import annotations

from bootstrap.configs.component import Component
from bootstrap.dependencies.settings import get_settings


def main() -> None:
    """Dispatch to the component specified by GLAC_COMPONENT."""
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


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run tests**

Run: `UV_RUN pytest -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add entrypoint.py
git commit -m "refactor(entrypoint): use settings.component instead of os.environ ROLE"
```

---

### Task 5: Refactor bootstrap/scheduler.py to use get_settings()

**Files:**
- Modify: `bootstrap/scheduler.py`

- [ ] **Step 1: Write the failing test**

Add `tests/bootstrap/test_scheduler_bootstrap.py`:

```python
"""Tests for scheduler bootstrap wiring."""

from __future__ import annotations

from unittest.mock import patch

from adapter.inbound.scheduler.scheduler_loop import SchedulerLoop


def test_build_scheduler_returns_scheduler_loop(monkeypatch):
    """Verify build_scheduler creates a SchedulerLoop with correct interval."""
    monkeypatch.setenv("GLAC_DATABASE_BACKEND", "sqlite")
    monkeypatch.setenv("GLAC_SQLITE__DB_PATH", ":memory:")
    monkeypatch.setenv("GLAC_SCHEDULER__INTERVAL_SECONDS", "45")

    from bootstrap.dependencies.settings import get_settings
    get_settings.cache_clear()

    from bootstrap.scheduler import build_scheduler

    loop = build_scheduler()
    assert isinstance(loop, SchedulerLoop)
    assert loop._interval_seconds == 45
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_RUN pytest tests/bootstrap/test_scheduler_bootstrap.py -v`
Expected: FAIL — `build_scheduler` still uses `os.environ.get`

- [ ] **Step 3: Rewrite bootstrap/scheduler.py**

```python
"""Scheduler entry point — polls DB and writes trigger events to outbox."""

from __future__ import annotations

import logging
import signal
from datetime import UTC, datetime

from adapter.inbound.scheduler.scheduler_loop import SchedulerLoop
from adapter.outbound.job.sql.jobs_sql_repo import JobsSqlRepo
from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from adapter.outbound.sql.engine_factory import build_engine
from adapter.outbound.sql.metadata import metadata
from application.service.outbox.event_serializer import EventSerializer
from application.service.scheduling.schedule_jobs import ScheduleJobsService
from bootstrap.dependencies.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_scheduler() -> SchedulerLoop:
    """Wire up the scheduler with SQL repos and return the loop."""
    settings = get_settings()
    engine = build_engine(settings)
    metadata.create_all(engine)

    jobs_repo = JobsSqlRepo(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    outbox_repo = EventOutboxSqlRepo(engine)
    serializer = EventSerializer()

    service = ScheduleJobsService(
        jobs_repo,
        job_runs_repo,
        clock=lambda: datetime.now(UTC),
        outbox_repo=outbox_repo,
        serializer=serializer,
    )
    return SchedulerLoop(service, interval_seconds=settings.scheduler.interval_seconds)


def main() -> None:
    """Start the scheduler."""
    scheduler = build_scheduler()
    signal.signal(signal.SIGTERM, lambda *_: scheduler.stop())
    signal.signal(signal.SIGINT, lambda *_: scheduler.stop())
    logger.info("Starting table-maintenance scheduler")
    scheduler.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `UV_RUN pytest tests/bootstrap/test_scheduler_bootstrap.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `UV_RUN pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add bootstrap/scheduler.py tests/bootstrap/test_scheduler_bootstrap.py
git commit -m "refactor(scheduler): use get_settings() instead of os.environ"
```

---

### Task 6: Refactor bootstrap/messaging.py to use get_settings()

**Files:**
- Modify: `bootstrap/messaging.py`

- [ ] **Step 1: Write the failing test**

Add `tests/bootstrap/test_messaging_bootstrap.py`:

```python
"""Tests for messaging bootstrap wiring."""

from __future__ import annotations

from adapter.inbound.messaging.outbox.publisher_loop import PublisherLoop


def test_build_publisher_returns_publisher_loop(monkeypatch):
    """Verify build_publisher creates a PublisherLoop with correct interval."""
    monkeypatch.setenv("GLAC_DATABASE_BACKEND", "sqlite")
    monkeypatch.setenv("GLAC_SQLITE__DB_PATH", ":memory:")
    monkeypatch.setenv("GLAC_MESSAGING__INTERVAL_SECONDS", "15")

    from bootstrap.dependencies.settings import get_settings
    get_settings.cache_clear()

    from bootstrap.messaging import build_publisher

    loop = build_publisher()
    assert isinstance(loop, PublisherLoop)
    assert loop._interval_seconds == 15
```

- [ ] **Step 2: Run test to verify it fails**

Run: `UV_RUN pytest tests/bootstrap/test_messaging_bootstrap.py -v`
Expected: FAIL — `build_publisher` still uses `os.environ.get`

- [ ] **Step 3: Rewrite bootstrap/messaging.py**

```python
"""Outbox publisher entry point — polls outbox table and dispatches events."""

from __future__ import annotations

import logging
import signal

from adapter.inbound.messaging.outbox.publisher_loop import PublisherLoop
from adapter.outbound.job_run.sql.job_runs_sql_repo import JobRunsSqlRepo
from adapter.outbound.sql.engine_factory import build_engine
from adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo
from adapter.outbound.sql.metadata import metadata
from application.domain.model.job.events import JobTriggered
from application.service.job_run.job_triggered_handler import JobTriggeredHandler
from application.service.outbox.event_serializer import EventSerializer
from application.service.outbox.publish_events import PublishEventsService
from base.event_dispatcher import EventDispatcher
from bootstrap.dependencies.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_publisher() -> PublisherLoop:
    """Wire up the outbox publisher with SQL repos and return the loop."""
    settings = get_settings()
    engine = build_engine(settings)
    metadata.create_all(engine)

    outbox_repo = EventOutboxSqlRepo(engine)
    job_runs_repo = JobRunsSqlRepo(engine)
    serializer = EventSerializer()

    dispatcher = EventDispatcher()
    dispatcher.register(
        JobTriggered,
        JobTriggeredHandler(job_runs_repo, outbox_repo, serializer),
    )

    service = PublishEventsService(outbox_repo, serializer, dispatcher)
    return PublisherLoop(service, interval_seconds=settings.messaging.interval_seconds)


def main() -> None:
    """Start the outbox publisher."""
    publisher = build_publisher()
    signal.signal(signal.SIGTERM, lambda *_: publisher.stop())
    signal.signal(signal.SIGINT, lambda *_: publisher.stop())
    logger.info("Starting outbox publisher")
    publisher.start()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `UV_RUN pytest tests/bootstrap/test_messaging_bootstrap.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `UV_RUN pytest -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add bootstrap/messaging.py tests/bootstrap/test_messaging_bootstrap.py
git commit -m "refactor(messaging): use get_settings() instead of os.environ"
```

---

### Task 7: Update CLAUDE.md and K8s manifests

**Files:**
- Modify: `CLAUDE.md` (project root)
- Modify: K8s deployment YAMLs (if in scope)

- [ ] **Step 1: Update CLAUDE.md**

Change env var references:
- `ROLE=api` → `GLAC_COMPONENT=api`
- `ROLE=scheduler` → `GLAC_COMPONENT=scheduler`
- Mention `GLAC_` as the env prefix

In the Rules section, update:
```
- **Single image, triple role**: `GLAC_COMPONENT=api` (default), `GLAC_COMPONENT=scheduler`, or `GLAC_COMPONENT=messaging` via `entrypoint.py`.
```

- [ ] **Step 2: Update K8s manifests**

In `25-tbl-maint-bcknd/backend-deployment.yaml`, change `ROLE` to `GLAC_COMPONENT` and `BACKEND_` to `GLAC_`.
In `25-tbl-maint-schdlr/scheduler-deployment.yaml`, change `ROLE` to `GLAC_COMPONENT` and `SCHEDULER_` to `GLAC_SCHEDULER__`.

- [ ] **Step 3: Run full verification**

```bash
UV_RUN pytest -v && UV_RUN ruff check . && UV_RUN lint-imports
```

Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs(config): update CLAUDE.md and K8s manifests for GLAC_ prefix"
```

---

### Task 8: Final cleanup and verification

- [ ] **Step 1: Verify no stale env var references remain**

```bash
grep -rn "BACKEND_\|SCHEDULER_DATABASE_URL\|SCHEDULER_INTERVAL_SECONDS\|OUTBOX_DATABASE_URL\|OUTBOX_INTERVAL_SECONDS\|\"ROLE\"" --include="*.py" | grep -v __pycache__ | grep -v .venv
```

Expected: No output.

- [ ] **Step 2: Verify no bare os.environ.get in bootstrap/**

```bash
grep -rn "os.environ" bootstrap/ --include="*.py"
```

Expected: No output.

- [ ] **Step 3: Run full verification suite**

```bash
UV_RUN pytest -v && UV_RUN ruff check . && UV_RUN lint-imports
```

Expected: All PASS, 0 broken contracts.

- [ ] **Step 4: Commit if any cleanup needed**

```bash
git diff --quiet || (git add -A && git commit -m "chore: clean up stale env var references")
```
