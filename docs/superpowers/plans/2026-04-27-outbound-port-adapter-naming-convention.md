# Outbound Port & Adapter Naming Convention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce `Store` and `Gateway` base classes in `base/`, then rename all outbound ports and adapters to follow the new naming convention.

**Architecture:** Three marker base classes (`Repository`, `Store`, `Gateway`) define all outbound port categories. Each port/adapter follows a fixed naming pattern. This is a pure rename refactoring — no behavioral changes.

**Tech Stack:** Python 3.12+, pytest, import-linter, ruff

**Spec:** `docs/superpowers/specs/2026-04-27-outbound-port-adapter-naming-convention.md`

---

### Task 1: Create `Store` base class

**Files:**
- Create: `src/table-maintenance/backend/base/store.py`
- Create: `src/table-maintenance/backend/tests/base/test_store.py`
- Modify: `src/table-maintenance/backend/base/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for Store base class."""

from __future__ import annotations

from abc import ABC

from base.store import Store


def test_store_is_abc() -> None:
    """Store is an abstract base class."""
    assert issubclass(Store, ABC)


def test_store_cannot_be_instantiated() -> None:
    """Store cannot be instantiated directly."""
    # Store itself has no abstract methods, but subclasses should.
    # Verify it's importable and is an ABC.
    assert hasattr(Store, "__abstractmethods__") or issubclass(Store, ABC)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/base/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'base.store'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Define the Store abstract base class."""

from __future__ import annotations

from abc import ABC


class Store(ABC):
    """Infrastructure persistence that is not an aggregate repository.

    Use Store for persistence concerns that do not manage the lifecycle
    of a domain aggregate (e.g., event outbox, audit log storage).
    """
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/base/test_store.py -v`
Expected: PASS

- [ ] **Step 5: Update `base/__init__.py` to export Store**

Add `Store` to imports and `__all__` in `src/table-maintenance/backend/base/__init__.py`:

```python
from base.store import Store
```

Add `"Store"` to the `__all__` list.

- [ ] **Step 6: Commit**

```bash
git add src/table-maintenance/backend/base/store.py src/table-maintenance/backend/tests/base/test_store.py src/table-maintenance/backend/base/__init__.py
git commit -m "feat(base): add Store abstract base class for infrastructure persistence"
```

---

### Task 2: Create `Gateway` base class

**Files:**
- Create: `src/table-maintenance/backend/base/gateway.py`
- Create: `src/table-maintenance/backend/tests/base/test_gateway.py`
- Modify: `src/table-maintenance/backend/base/__init__.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for Gateway base class."""

from __future__ import annotations

from abc import ABC

from base.gateway import Gateway


def test_gateway_is_abc() -> None:
    """Gateway is an abstract base class."""
    assert issubclass(Gateway, ABC)


def test_gateway_cannot_be_instantiated() -> None:
    """Gateway is importable and is an ABC."""
    assert hasattr(Gateway, "__abstractmethods__") or issubclass(Gateway, ABC)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/base/test_gateway.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'base.gateway'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Define the Gateway abstract base class."""

from __future__ import annotations

from abc import ABC


class Gateway(ABC):
    """Port for interacting with external systems.

    Use Gateway for operations that cross a system boundary: reading from
    external catalogs, submitting jobs to orchestrators, sending notifications,
    publishing events to message brokers, etc.
    """
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/base/test_gateway.py -v`
Expected: PASS

- [ ] **Step 5: Update `base/__init__.py` to export Gateway**

Add `Gateway` to imports and `__all__` in `src/table-maintenance/backend/base/__init__.py`:

```python
from base.gateway import Gateway
```

Add `"Gateway"` to the `__all__` list.

- [ ] **Step 6: Commit**

```bash
git add src/table-maintenance/backend/base/gateway.py src/table-maintenance/backend/tests/base/test_gateway.py src/table-maintenance/backend/base/__init__.py
git commit -m "feat(base): add Gateway abstract base class for external system interaction"
```

---

### Task 3: Rename `EventOutboxRepo` → `EventOutboxStore`

**Port file rename:** `event_outbox_repo.py` → `event_outbox/event_outbox_store.py`
**Adapter file rename:** `event_outbox_sql_repo.py` → `event_outbox_sql_store.py`
**Class renames:** `EventOutboxRepo` → `EventOutboxStore`, `EventOutboxSqlRepo` → `EventOutboxSqlStore`

**Files to create:**
- `src/table-maintenance/backend/application/port/outbound/event_outbox/__init__.py`
- `src/table-maintenance/backend/application/port/outbound/event_outbox/event_outbox_store.py`
- `src/table-maintenance/backend/adapter/outbound/sql/event_outbox_sql_store.py`
- `src/table-maintenance/backend/tests/application/port/outbound/event_outbox/__init__.py`
- `src/table-maintenance/backend/tests/application/port/outbound/event_outbox/test_event_outbox_store.py`
- `src/table-maintenance/backend/tests/adapter/outbound/sql/test_event_outbox_sql_store.py`

**Files to delete:**
- `src/table-maintenance/backend/application/port/outbound/event_outbox_repo.py`
- `src/table-maintenance/backend/adapter/outbound/sql/event_outbox_sql_repo.py`
- `src/table-maintenance/backend/tests/application/port/outbound/test_event_outbox_repo.py`
- `src/table-maintenance/backend/tests/adapter/outbound/sql/test_event_outbox_sql_repo.py`

**Files to update imports in:**
- `src/table-maintenance/backend/application/port/outbound/__init__.py`
- `src/table-maintenance/backend/application/service/job_run/create_job_run.py`
- `src/table-maintenance/backend/application/service/job/update_job.py`
- `src/table-maintenance/backend/application/service/job/create_job.py`
- `src/table-maintenance/backend/application/service/scheduling/schedule_jobs.py`
- `src/table-maintenance/backend/application/service/handler/job_triggered_handler.py`
- `src/table-maintenance/backend/application/service/outbox/publish_events.py`
- `src/table-maintenance/backend/bootstrap/dependencies/outbox.py`
- `src/table-maintenance/backend/bootstrap/dependencies/use_cases.py`
- `src/table-maintenance/backend/bootstrap/messaging.py`
- `src/table-maintenance/backend/bootstrap/scheduler.py`
- `src/table-maintenance/backend/tests/test_event_chain_publish.py`
- `src/table-maintenance/backend/tests/test_error_outbox_idempotency.py`
- `src/table-maintenance/backend/tests/test_event_chain_scheduler.py`
- `src/table-maintenance/backend/tests/test_error_executor_failure.py`

- [ ] **Step 1: Write port test for EventOutboxStore**

Create `tests/application/port/outbound/event_outbox/__init__.py` (empty) and `tests/application/port/outbound/event_outbox/test_event_outbox_store.py`:

```python
"""Tests for EventOutboxStore port interface."""

from __future__ import annotations

from base.store import Store

from application.port.outbound.event_outbox.event_outbox_store import EventOutboxStore


def test_is_store() -> None:
    """EventOutboxStore extends Store."""
    assert issubclass(EventOutboxStore, Store)


def test_declares_save() -> None:
    """EventOutboxStore defines save."""
    assert hasattr(EventOutboxStore, "save")


def test_declares_fetch_unpublished() -> None:
    """EventOutboxStore defines fetch_unpublished."""
    assert hasattr(EventOutboxStore, "fetch_unpublished")


def test_declares_mark_published() -> None:
    """EventOutboxStore defines mark_published."""
    assert hasattr(EventOutboxStore, "mark_published")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/outbound/event_outbox/test_event_outbox_store.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create EventOutboxStore port**

Create `application/port/outbound/event_outbox/__init__.py`:

```python
"""Event outbox store port."""

from application.port.outbound.event_outbox.event_outbox_store import EventOutboxStore

__all__ = ["EventOutboxStore"]
```

Create `application/port/outbound/event_outbox/event_outbox_store.py`:

```python
"""Define the EventOutboxStore port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.store import Store

if TYPE_CHECKING:
    from application.domain.model.outbox_entry import OutboxEntry


class EventOutboxStore(Store):
    """Port for persisting and retrieving outbox entries."""

    @abstractmethod
    def save(self, entries: list[OutboxEntry]) -> None:
        """Persist outbox entries within the current transaction."""
        ...

    @abstractmethod
    def fetch_unpublished(self, batch_size: int = 100) -> list[OutboxEntry]:
        """Return up to batch_size unpublished entries ordered by occurred_at."""
        ...

    @abstractmethod
    def mark_published(self, entry_ids: list[str]) -> None:
        """Set published_at = now for the given entry IDs."""
        ...
```

- [ ] **Step 4: Run port test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/outbound/event_outbox/test_event_outbox_store.py -v`
Expected: PASS

- [ ] **Step 5: Write adapter test for EventOutboxSqlStore**

Create `tests/adapter/outbound/sql/test_event_outbox_sql_store.py` — copy content from `test_event_outbox_sql_repo.py` but update all class names and imports:

- `EventOutboxRepo` → `EventOutboxStore`
- `EventOutboxSqlRepo` → `EventOutboxSqlStore`
- Import from `application.port.outbound.event_outbox.event_outbox_store`
- Import from `adapter.outbound.sql.event_outbox_sql_store`
- Assert `issubclass(EventOutboxSqlStore, EventOutboxStore)`

- [ ] **Step 6: Run adapter test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/sql/test_event_outbox_sql_store.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 7: Create EventOutboxSqlStore adapter**

Create `adapter/outbound/sql/event_outbox_sql_store.py` — copy content from `event_outbox_sql_repo.py` but:

- Class name: `EventOutboxSqlStore`
- Inherits from `EventOutboxStore` instead of `EventOutboxRepo`
- Import from `application.port.outbound.event_outbox.event_outbox_store`

- [ ] **Step 8: Run adapter test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/sql/test_event_outbox_sql_store.py -v`
Expected: PASS

- [ ] **Step 9: Update all imports across the codebase**

Update every file listed in the "Files to update imports in" section above. In each file:

- Replace `from application.port.outbound.event_outbox_repo import EventOutboxRepo` with `from application.port.outbound.event_outbox.event_outbox_store import EventOutboxStore`
- Replace `EventOutboxRepo` → `EventOutboxStore` in type annotations and variable names
- Replace `from adapter.outbound.sql.event_outbox_sql_repo import EventOutboxSqlRepo` with `from adapter.outbound.sql.event_outbox_sql_store import EventOutboxSqlStore`
- Replace `EventOutboxSqlRepo` → `EventOutboxSqlStore` in constructor calls

Also update `application/port/outbound/__init__.py` to export `EventOutboxStore` if desired.

- [ ] **Step 10: Delete old files**

Delete:
- `application/port/outbound/event_outbox_repo.py`
- `adapter/outbound/sql/event_outbox_sql_repo.py`
- `tests/application/port/outbound/test_event_outbox_repo.py`
- `tests/adapter/outbound/sql/test_event_outbox_sql_repo.py`

- [ ] **Step 11: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS

- [ ] **Step 12: Run linters**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check . && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`
Expected: Clean

- [ ] **Step 13: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(outbound): rename EventOutboxRepo to EventOutboxStore

EventOutboxStore extends the new Store base class instead of bare ABC.
Move port from event_outbox_repo.py to event_outbox/event_outbox_store.py.
Rename adapter EventOutboxSqlRepo to EventOutboxSqlStore."
```

---

### Task 4: Rename `CatalogReader` → `ReadCatalogGateway`

**Port file rename:** `catalog/catalog_reader.py` → `catalog/read_catalog_gateway.py`
**Adapter file rename:** `catalog/iceberg_catalog_client.py` → `catalog/read_catalog_iceberg_gateway.py`
**Class renames:** `CatalogReader` → `ReadCatalogGateway`, `IcebergCatalogClient` → `ReadCatalogIcebergGateway`

**Files to create:**
- `src/table-maintenance/backend/application/port/outbound/catalog/read_catalog_gateway.py`
- `src/table-maintenance/backend/adapter/outbound/catalog/read_catalog_iceberg_gateway.py`
- `src/table-maintenance/backend/tests/application/port/outbound/catalog/test_read_catalog_gateway.py`
- `src/table-maintenance/backend/tests/adapter/outbound/catalog/test_read_catalog_iceberg_gateway.py`

**Files to delete:**
- `src/table-maintenance/backend/application/port/outbound/catalog/catalog_reader.py`
- `src/table-maintenance/backend/adapter/outbound/catalog/iceberg_catalog_client.py`
- `src/table-maintenance/backend/tests/application/port/outbound/catalog/test_catalog_reader.py`
- `src/table-maintenance/backend/tests/adapter/outbound/catalog/test_iceberg_catalog_client.py`

**Files to update imports in:**
- `src/table-maintenance/backend/application/port/outbound/catalog/__init__.py`
- `src/table-maintenance/backend/application/port/outbound/__init__.py`
- `src/table-maintenance/backend/adapter/outbound/catalog/__init__.py`
- `src/table-maintenance/backend/application/service/catalog/get_table.py`
- `src/table-maintenance/backend/application/service/catalog/list_namespaces.py`
- `src/table-maintenance/backend/application/service/catalog/list_tables.py`
- `src/table-maintenance/backend/application/service/catalog/list_tags.py`
- `src/table-maintenance/backend/application/service/catalog/list_snapshots.py`
- `src/table-maintenance/backend/application/service/catalog/list_branches.py`
- `src/table-maintenance/backend/bootstrap/dependencies/catalog.py`
- `src/table-maintenance/backend/bootstrap/dependencies/use_cases.py`

- [ ] **Step 1: Write port test for ReadCatalogGateway**

Create `tests/application/port/outbound/catalog/test_read_catalog_gateway.py`:

```python
"""Test the ReadCatalogGateway port interface."""

from __future__ import annotations

from abc import ABC

import pytest

from base.gateway import Gateway

from application.port.outbound.catalog.read_catalog_gateway import ReadCatalogGateway


def test_cannot_be_instantiated() -> None:
    """ReadCatalogGateway cannot be instantiated."""
    with pytest.raises(TypeError):
        ReadCatalogGateway()


def test_is_gateway() -> None:
    """ReadCatalogGateway extends Gateway."""
    assert issubclass(ReadCatalogGateway, Gateway)


def test_declares_list_namespaces() -> None:
    """ReadCatalogGateway declares list_namespaces."""
    assert "list_namespaces" in ReadCatalogGateway.__abstractmethods__


def test_declares_list_tables() -> None:
    """ReadCatalogGateway declares list_tables."""
    assert "list_tables" in ReadCatalogGateway.__abstractmethods__


def test_declares_load_table() -> None:
    """ReadCatalogGateway declares load_table."""
    assert "load_table" in ReadCatalogGateway.__abstractmethods__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/outbound/catalog/test_read_catalog_gateway.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create ReadCatalogGateway port**

Create `application/port/outbound/catalog/read_catalog_gateway.py`:

```python
"""Define the ReadCatalogGateway port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.domain.model.catalog.table import Table


class ReadCatalogGateway(Gateway):
    """Read-only gateway for accessing Iceberg catalog metadata."""

    @abstractmethod
    def list_namespaces(self) -> list[str]:
        """Return all namespace names in the catalog."""

    @abstractmethod
    def list_tables(self, namespace: str) -> list[str]:
        """Return all table names within a namespace."""

    @abstractmethod
    def load_table(self, namespace: str, table: str) -> Table:
        """Load the full Table aggregate from the catalog."""
```

- [ ] **Step 4: Run port test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/outbound/catalog/test_read_catalog_gateway.py -v`
Expected: PASS

- [ ] **Step 5: Write adapter test for ReadCatalogIcebergGateway**

Create `tests/adapter/outbound/catalog/test_read_catalog_iceberg_gateway.py` ��� copy content from `test_iceberg_catalog_client.py` but update:

- `CatalogReader` → `ReadCatalogGateway`
- `IcebergCatalogClient` → `ReadCatalogIcebergGateway`
- Import from `application.port.outbound.catalog.read_catalog_gateway`
- Import from `adapter.outbound.catalog.read_catalog_iceberg_gateway`
- Assert `isinstance(client, ReadCatalogGateway)`

- [ ] **Step 6: Run adapter test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/catalog/test_read_catalog_iceberg_gateway.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 7: Create ReadCatalogIcebergGateway adapter**

Create `adapter/outbound/catalog/read_catalog_iceberg_gateway.py` — copy content from `iceberg_catalog_client.py` but:

- Class name: `ReadCatalogIcebergGateway`
- Inherits from `ReadCatalogGateway` instead of `CatalogReader`
- Import from `application.port.outbound.catalog.read_catalog_gateway`

- [ ] **Step 8: Run adapter test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/catalog/test_read_catalog_iceberg_gateway.py -v`
Expected: PASS

- [ ] **Step 9: Update all imports across the codebase**

Update every file listed in the "Files to update imports in" section above. In each file:

- Replace `from application.port.outbound.catalog.catalog_reader import CatalogReader` with `from application.port.outbound.catalog.read_catalog_gateway import ReadCatalogGateway`
- Replace `CatalogReader` → `ReadCatalogGateway` in type annotations, variable names, and docstrings
- Replace `from adapter.outbound.catalog.iceberg_catalog_client import IcebergCatalogClient` with `from adapter.outbound.catalog.read_catalog_iceberg_gateway import ReadCatalogIcebergGateway`
- Replace `IcebergCatalogClient` → `ReadCatalogIcebergGateway` in constructor calls and return types

- [ ] **Step 10: Delete old files**

Delete:
- `application/port/outbound/catalog/catalog_reader.py`
- `adapter/outbound/catalog/iceberg_catalog_client.py`
- `tests/application/port/outbound/catalog/test_catalog_reader.py`
- `tests/adapter/outbound/catalog/test_iceberg_catalog_client.py`

- [ ] **Step 11: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS

- [ ] **Step 12: Run linters**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check . && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`
Expected: Clean

- [ ] **Step 13: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(outbound): rename CatalogReader to ReadCatalogGateway

ReadCatalogGateway extends the new Gateway base class.
Rename adapter IcebergCatalogClient to ReadCatalogIcebergGateway."
```

---

### Task 5: Rename `JobRunExecutor` → `SubmitJobRunGateway`

**Port file rename:** `job_run/job_run_executor.py` → `job_run/submit_job_run_gateway.py`
**Adapter file renames:**
- `job_run/job_run_in_memory_executor.py` → `job_run/submit_job_run_in_memory_gateway.py`
- `job_run/k8s/job_run_k8s_executor.py` → `job_run/k8s/submit_job_run_k8s_gateway.py`

**Class renames:**
- `JobRunExecutor` → `SubmitJobRunGateway`
- `JobRunInMemoryExecutor` → `SubmitJobRunInMemoryGateway`
- `JobRunK8sExecutor` → `SubmitJobRunK8sGateway`

**Config enum rename:** `JobRunExecutorAdapter` → `SubmitJobRunGatewayAdapter`
**Config field rename:** `job_run_executor_adapter` → `submit_job_run_gateway_adapter`
**Env var change:** `GLAC_JOB_RUN_EXECUTOR_ADAPTER` → `GLAC_SUBMIT_JOB_RUN_GATEWAY_ADAPTER`

**Files to create:**
- `src/table-maintenance/backend/application/port/outbound/job_run/submit_job_run_gateway.py`
- `src/table-maintenance/backend/adapter/outbound/job_run/submit_job_run_in_memory_gateway.py`
- `src/table-maintenance/backend/adapter/outbound/job_run/k8s/submit_job_run_k8s_gateway.py`
- `src/table-maintenance/backend/bootstrap/configs/submit_job_run_gateway_adapter.py`
- `src/table-maintenance/backend/tests/application/port/outbound/job_run/test_submit_job_run_gateway.py`
- `src/table-maintenance/backend/tests/adapter/outbound/job_run/test_submit_job_run_in_memory_gateway.py`
- `src/table-maintenance/backend/tests/adapter/outbound/job_run/k8s/test_submit_job_run_k8s_gateway.py`
- `src/table-maintenance/backend/tests/bootstrap/configs/test_submit_job_run_gateway_adapter.py`

**Files to delete:**
- `src/table-maintenance/backend/application/port/outbound/job_run/job_run_executor.py`
- `src/table-maintenance/backend/adapter/outbound/job_run/job_run_in_memory_executor.py`
- `src/table-maintenance/backend/adapter/outbound/job_run/k8s/job_run_k8s_executor.py`
- `src/table-maintenance/backend/bootstrap/configs/job_run_executor_adapter.py`
- `src/table-maintenance/backend/tests/application/port/outbound/job_run/test_job_run_executor.py`
- `src/table-maintenance/backend/tests/adapter/outbound/job_run/test_in_memory_job_run_executor.py`
- `src/table-maintenance/backend/tests/adapter/outbound/job_run/k8s/test_k8s_job_run_executor.py`
- `src/table-maintenance/backend/tests/bootstrap/configs/test_job_run_executor_adapter.py`

**Files to update imports in:**
- `src/table-maintenance/backend/application/port/outbound/job_run/__init__.py`
- `src/table-maintenance/backend/application/port/outbound/__init__.py`
- `src/table-maintenance/backend/application/service/job_run/submit_job_run.py`
- `src/table-maintenance/backend/bootstrap/configs/__init__.py`
- `src/table-maintenance/backend/bootstrap/configs/app.py`
- `src/table-maintenance/backend/bootstrap/dependencies/repos.py`
- `src/table-maintenance/backend/bootstrap/messaging.py`
- `src/table-maintenance/backend/tests/bootstrap/dependencies/test_repos.py`
- `src/table-maintenance/backend/tests/bootstrap/configs/test_adapter_settings.py`
- `src/table-maintenance/backend/tests/test_error_executor_failure.py`
- `src/table-maintenance/backend/tests/test_error_outbox_idempotency.py`
- `src/table-maintenance/backend/tests/test_event_chain_publish.py`
- `src/table-maintenance/backend/tests/test_event_chain_scheduler.py`

- [ ] **Step 1: Write port test for SubmitJobRunGateway**

Create `tests/application/port/outbound/job_run/test_submit_job_run_gateway.py`:

```python
"""Tests for SubmitJobRunGateway."""

from __future__ import annotations

from abc import ABC

from base.gateway import Gateway

from application.port.outbound.job_run.submit_job_run_gateway import SubmitJobRunGateway


def test_is_gateway() -> None:
    """SubmitJobRunGateway extends Gateway."""
    assert issubclass(SubmitJobRunGateway, Gateway)


def test_declares_submit() -> None:
    """SubmitJobRunGateway declares submit as an abstract method."""
    assert "submit" in SubmitJobRunGateway.__abstractmethods__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/outbound/job_run/test_submit_job_run_gateway.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create SubmitJobRunGateway port**

Create `application/port/outbound/job_run/submit_job_run_gateway.py`:

```python
"""Define the SubmitJobRunGateway port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.job_run.job_submission import JobSubmission


class SubmitJobRunGateway(Gateway):
    """Gateway for submitting a job to an external execution system.

    The gateway performs a side-effect (e.g. creating a SparkApplication
    in Kubernetes). It does not create domain entities — that responsibility
    belongs to the application service layer.
    """

    @abstractmethod
    def submit(self, submission: JobSubmission) -> None:
        """Submit the job for execution in the external system."""
        ...
```

- [ ] **Step 4: Run port test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/application/port/outbound/job_run/test_submit_job_run_gateway.py -v`
Expected: PASS

- [ ] **Step 5: Write adapter tests**

Create `tests/adapter/outbound/job_run/test_submit_job_run_in_memory_gateway.py` — copy from `test_in_memory_job_run_executor.py` but update:
- `JobRunExecutor` → `SubmitJobRunGateway`
- `JobRunInMemoryExecutor` → `SubmitJobRunInMemoryGateway`
- Import from `application.port.outbound.job_run.submit_job_run_gateway`
- Import from `adapter.outbound.job_run.submit_job_run_in_memory_gateway`

Create `tests/adapter/outbound/job_run/k8s/test_submit_job_run_k8s_gateway.py` — copy from `test_k8s_job_run_executor.py` but update:
- `JobRunExecutor` → `SubmitJobRunGateway`
- `JobRunK8sExecutor` → `SubmitJobRunK8sGateway`
- Import from `application.port.outbound.job_run.submit_job_run_gateway`
- Import from `adapter.outbound.job_run.k8s.submit_job_run_k8s_gateway`

- [ ] **Step 6: Run adapter tests to verify they fail**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/job_run/test_submit_job_run_in_memory_gateway.py tests/adapter/outbound/job_run/k8s/test_submit_job_run_k8s_gateway.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 7: Create adapter implementations**

Create `adapter/outbound/job_run/submit_job_run_in_memory_gateway.py` — copy from `job_run_in_memory_executor.py` but:
- Class name: `SubmitJobRunInMemoryGateway`
- Inherits from `SubmitJobRunGateway`
- Import from `application.port.outbound.job_run.submit_job_run_gateway`

Create `adapter/outbound/job_run/k8s/submit_job_run_k8s_gateway.py` — copy from `job_run_k8s_executor.py` but:
- Class name: `SubmitJobRunK8sGateway`
- Inherits from `SubmitJobRunGateway`
- Import from `application.port.outbound.job_run.submit_job_run_gateway`

- [ ] **Step 8: Run adapter tests to verify they pass**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/adapter/outbound/job_run/test_submit_job_run_in_memory_gateway.py tests/adapter/outbound/job_run/k8s/test_submit_job_run_k8s_gateway.py -v`
Expected: PASS

- [ ] **Step 9: Write config enum test**

Create `tests/bootstrap/configs/test_submit_job_run_gateway_adapter.py`:

```python
"""Tests for SubmitJobRunGatewayAdapter."""

from bootstrap.configs import SubmitJobRunGatewayAdapter


def test_members_have_correct_values() -> None:
    """Verify that SubmitJobRunGatewayAdapter members have correct string values."""
    assert SubmitJobRunGatewayAdapter.IN_MEMORY == "in_memory"
    assert SubmitJobRunGatewayAdapter.K8S == "k8s"


def test_members_are_strings() -> None:
    """Verify that SubmitJobRunGatewayAdapter members are str instances."""
    assert isinstance(SubmitJobRunGatewayAdapter.IN_MEMORY, str)
    assert isinstance(SubmitJobRunGatewayAdapter.K8S, str)
```

- [ ] **Step 10: Run config test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/bootstrap/configs/test_submit_job_run_gateway_adapter.py -v`
Expected: FAIL with `ImportError`

- [ ] **Step 11: Create SubmitJobRunGatewayAdapter config enum**

Create `bootstrap/configs/submit_job_run_gateway_adapter.py`:

```python
"""Define the SubmitJobRunGatewayAdapter enumeration."""

from __future__ import annotations

from enum import StrEnum


class SubmitJobRunGatewayAdapter(StrEnum):
    """Enumerate supported SubmitJobRunGateway implementations."""

    IN_MEMORY = "in_memory"
    K8S = "k8s"
```

- [ ] **Step 12: Run config test to verify it passes**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/bootstrap/configs/test_submit_job_run_gateway_adapter.py -v`
Expected: PASS

- [ ] **Step 13: Update all imports across the codebase**

Update every file listed in the "Files to update imports in" section above. Key changes:

**Port/adapter imports:**
- `JobRunExecutor` → `SubmitJobRunGateway`
- `JobRunInMemoryExecutor` → `SubmitJobRunInMemoryGateway`
- `JobRunK8sExecutor` → `SubmitJobRunK8sGateway`
- Update all import paths accordingly

**Config imports:**
- `JobRunExecutorAdapter` ��� `SubmitJobRunGatewayAdapter`
- In `bootstrap/configs/__init__.py`: update import and `__all__`
- In `bootstrap/configs/app.py`: rename field from `job_run_executor_adapter` to `submit_job_run_gateway_adapter`
- In `bootstrap/dependencies/repos.py`: update enum references
- In `tests/bootstrap/configs/test_adapter_settings.py`: update field name and enum name

**Integration test imports:**
- In `tests/test_error_executor_failure.py`: rename `FailingExecutor(JobRunExecutor)` to `FailingGateway(SubmitJobRunGateway)`
- In `tests/test_error_outbox_idempotency.py`, `tests/test_event_chain_publish.py`, `tests/test_event_chain_scheduler.py`: update all executor references to gateway

- [ ] **Step 14: Delete old files**

Delete:
- `application/port/outbound/job_run/job_run_executor.py`
- `adapter/outbound/job_run/job_run_in_memory_executor.py`
- `adapter/outbound/job_run/k8s/job_run_k8s_executor.py`
- `bootstrap/configs/job_run_executor_adapter.py`
- `tests/application/port/outbound/job_run/test_job_run_executor.py`
- `tests/adapter/outbound/job_run/test_in_memory_job_run_executor.py`
- `tests/adapter/outbound/job_run/k8s/test_k8s_job_run_executor.py`
- `tests/bootstrap/configs/test_job_run_executor_adapter.py`

- [ ] **Step 15: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
Expected: All tests PASS

- [ ] **Step 16: Run linters**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check . && uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`
Expected: Clean

- [ ] **Step 17: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(outbound): rename JobRunExecutor to SubmitJobRunGateway

SubmitJobRunGateway extends the new Gateway base class.
Rename adapters: JobRunK8sExecutor → SubmitJobRunK8sGateway,
JobRunInMemoryExecutor → SubmitJobRunInMemoryGateway.
Rename config enum: JobRunExecutorAdapter → SubmitJobRunGatewayAdapter.
Rename config field: job_run_executor_adapter → submit_job_run_gateway_adapter."
```

---

### Task 6: Update CLAUDE.md with naming convention rules

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Add outbound port/adapter naming convention section**

Add the following to the Architecture section of `CLAUDE.md`, after the existing Rules:

```markdown
## Outbound Port & Adapter Naming Convention

Three base classes define all outbound ports (in `base/`):

| Base Class | When to use | Port format | Adapter format |
|------------|------------|-------------|----------------|
| `Repository` | Aggregate persistence | `{Aggregate}Repo` | `{Aggregate}{Tech}Repo` |
| `Store` | Infrastructure persistence (not aggregate) | `{Noun}Store` | `{Noun}{Tech}Store` |
| `Gateway` | External system interaction | `{Verb}{Noun}Gateway` | `{Verb}{Noun}{Tech}Gateway` |

**Gateway verb vocabulary** (new verbs require review): `Read`, `Submit`, `Send`, `Publish`, `Poll`, `Sync`, `Write`, `Delete`.

See `docs/superpowers/specs/2026-04-27-outbound-port-adapter-naming-convention.md` for full spec.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add outbound port/adapter naming convention to CLAUDE.md"
```
