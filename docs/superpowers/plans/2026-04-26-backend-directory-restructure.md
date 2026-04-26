# Backend Directory Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize backend directory to reflect hexagonal architecture: eliminate `core/`, create symmetric `adapter/inbound+outbound`, consolidate composition roots into `bootstrap/`.

**Architecture:** Layer-by-layer migration from innermost to outermost. Each task moves one architectural layer, updates all imports, and verifies with the full test suite. Architecture guard tests are written first (RED) then satisfied by the moves (GREEN).

**Tech Stack:** Python, pytest, import-linter, git mv, sed

**Working directory:** `src/table-maintenance/backend` (all paths relative to this unless noted)

**Commands:** All commands use `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend` prefix. Abbreviated as `UV_RUN` in this plan.

---

### Task 1: Write architecture guard test for new top-level structure (RED)

**Files:**
- Create: `tests/architecture/test_directory_structure.py`

This test asserts the target directory structure exists. It will FAIL initially (RED phase) and pass after all moves are complete.

- [ ] **Step 1: Write the failing test**

```python
"""Guard test: backend top-level directories match hexagonal architecture."""

from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]

EXPECTED_TOP_LEVEL = {"adapter", "application", "base", "bootstrap"}


class TestDirectoryStructure:
    """Verify the backend follows the target hexagonal layout."""

    @pytest.mark.parametrize("directory", sorted(EXPECTED_TOP_LEVEL))
    def test_required_directories_exist(self, directory: str):
        assert (BACKEND / directory).is_dir(), f"Missing required directory: {directory}/"

    def test_core_directory_does_not_exist(self):
        assert not (BACKEND / "core").is_dir(), (
            "core/ should not exist — its contents should be in "
            "adapter/, application/, base/, and bootstrap/"
        )

    @pytest.mark.parametrize(
        "subdir",
        ["adapter/inbound/web", "adapter/inbound/scheduler", "adapter/inbound/messaging/outbox", "adapter/outbound"],
    )
    def test_adapter_subdirectories_exist(self, subdir: str):
        assert (BACKEND / subdir).is_dir(), f"Missing adapter subdirectory: {subdir}/"

    @pytest.mark.parametrize(
        "subdir",
        ["bootstrap/configs", "bootstrap/dependencies"],
    )
    def test_bootstrap_subdirectories_exist(self, subdir: str):
        assert (BACKEND / subdir).is_dir(), f"Missing bootstrap subdirectory: {subdir}/"

    def test_no_stale_top_level_directories(self):
        """Top-level should not have old scattered entry point dirs."""
        for stale in ("api", "scheduler", "outbox_publisher", "dependencies"):
            assert not (BACKEND / stale).is_dir(), (
                f"{stale}/ should not exist at top level — "
                f"moved to adapter/inbound/ or bootstrap/"
            )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `UV_RUN pytest tests/architecture/test_directory_structure.py -v`
Expected: Multiple FAIL — `adapter/`, `application/`, `base/`, `bootstrap/` don't exist yet; `core/` still exists.

- [ ] **Step 3: Commit the RED test**

```bash
git add tests/architecture/test_directory_structure.py
git commit -m "test(arch): add guard test for new hexagonal directory structure (RED)"
```

---

### Task 2: Move `core/base/` to `base/`

**Files:**
- Move: `core/base/` → `base/`
- Modify: all files importing `core.base.*` (source + tests)

`base/` is the innermost layer with zero project dependencies, so it's safest to move first.

- [ ] **Step 1: Move the directory**

```bash
git mv core/base base_new && git mv base_new base
```

Note: `git mv core/base base` may fail if `base` doesn't exist at top level. Use a two-step rename if needed. If `base` doesn't exist, `git mv core/base base` should work directly — try that first.

- [ ] **Step 2: Update all imports from `core.base.` to `base.`**

```bash
# Source files
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/from core\.base\./from base./g; s/import core\.base\./import base./g'

# Also update any string references like "core.base" in __init__.py re-exports
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/"core\.base\./"base./g'
```

- [ ] **Step 3: Run the full test suite**

Run: `UV_RUN pytest -v`
Expected: All tests PASS (except the new architecture guard tests which are expected to fail — skip them with `-k "not test_directory_structure"` if needed).

- [ ] **Step 4: Run linters**

```bash
UV_RUN ruff check .
UV_RUN lint-imports
```

Fix any issues. The `.importlinter` still references `core.base` — update it:

Replace all `core.base` with `base` in `.importlinter`. Also add `base` to `root_packages`.

- [ ] **Step 5: Run tests + lint-imports again to verify**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(arch): move core/base/ to top-level base/"
```

---

### Task 3: Move `core/application/` to `application/`

**Files:**
- Move: `core/application/` → `application/`
- Modify: all files importing `core.application.*` (source + tests)

- [ ] **Step 1: Move the directory**

```bash
git mv core/application application
```

- [ ] **Step 2: Update all imports from `core.application.` to `application.`**

```bash
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/from core\.application\./from application./g; s/import core\.application\./import application./g'
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/"core\.application\./"application./g'
```

- [ ] **Step 3: Update `.importlinter`**

Replace all `core.application` with `application` in `.importlinter`. Also add `application` to `root_packages`, remove `core` if no longer referenced.

- [ ] **Step 4: Run full test suite + lint-imports**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(arch): move core/application/ to top-level application/"
```

---

### Task 4: Move `core/adapter/outbound/` to `adapter/outbound/`

**Files:**
- Move: `core/adapter/outbound/` → `adapter/outbound/`
- Modify: all files importing `core.adapter.outbound.*`

- [ ] **Step 1: Create the adapter directory and move**

```bash
mkdir -p adapter/inbound
git mv core/adapter/outbound adapter/outbound
```

Also create `adapter/__init__.py`, `adapter/inbound/__init__.py`, `adapter/outbound/__init__.py` if the move doesn't preserve them.

- [ ] **Step 2: Update all imports from `core.adapter.outbound.` to `adapter.outbound.`**

```bash
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/from core\.adapter\.outbound\./from adapter.outbound./g; s/import core\.adapter\.outbound\./import adapter.outbound./g'
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/"core\.adapter\.outbound\./"adapter.outbound./g'
```

- [ ] **Step 3: Update `.importlinter`**

Replace all `core.adapter.outbound` and `core.adapter` with `adapter.outbound` and `adapter`. Add `adapter` to `root_packages`.

- [ ] **Step 4: Delete the now-empty `core/adapter/` directory**

```bash
rm -rf core/adapter
```

- [ ] **Step 5: Run full test suite + lint-imports**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(arch): move core/adapter/outbound/ to adapter/outbound/"
```

---

### Task 5: Move `core/configs/` to `bootstrap/configs/`

**Files:**
- Move: `core/configs/` → `bootstrap/configs/`
- Modify: all files importing `core.configs.*`

- [ ] **Step 1: Create the bootstrap directory and move**

```bash
mkdir -p bootstrap
git mv core/configs bootstrap/configs
```

Create `bootstrap/__init__.py`.

- [ ] **Step 2: Update all imports from `core.configs.` to `bootstrap.configs.`**

```bash
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/from core\.configs/from bootstrap.configs/g; s/import core\.configs/import bootstrap.configs/g'
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/"core\.configs/"bootstrap.configs/g'
```

- [ ] **Step 3: Update `.importlinter`**

Replace all `core.configs` with `bootstrap.configs`. Add `bootstrap` to `root_packages`.

- [ ] **Step 4: Delete the now-empty `core/` directory**

```bash
rm -rf core
```

- [ ] **Step 5: Run full test suite + lint-imports**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(arch): move core/configs/ to bootstrap/configs/, eliminate core/"
```

---

### Task 6: Move `dependencies/` to `bootstrap/dependencies/`

**Files:**
- Move: `dependencies/` → `bootstrap/dependencies/`
- Modify: all files importing `dependencies.*`

- [ ] **Step 1: Move the directory**

```bash
git mv dependencies bootstrap/dependencies
```

- [ ] **Step 2: Update all imports from `dependencies.` to `bootstrap.dependencies.`**

```bash
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/from dependencies\./from bootstrap.dependencies./g; s/import dependencies\./import bootstrap.dependencies./g'
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/"dependencies\./"bootstrap.dependencies./g'
```

- [ ] **Step 3: Update `.importlinter`**

Replace all `dependencies` references with `bootstrap.dependencies`. Remove `dependencies` from `root_packages` (already covered by `bootstrap`).

- [ ] **Step 4: Update test directory**

```bash
git mv tests/dependencies tests/bootstrap
mkdir -p tests/bootstrap
# If tests/bootstrap already exists from the move, this is fine
```

Rename the test directory to match the new source layout. Update any imports in test files.

- [ ] **Step 5: Run full test suite + lint-imports**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(arch): move dependencies/ to bootstrap/dependencies/"
```

---

### Task 7: Move `api/adapter/inbound/web/` to `adapter/inbound/web/`

**Files:**
- Move: `api/adapter/inbound/web/` → `adapter/inbound/web/`
- Modify: all files importing `api.adapter.inbound.web.*`

- [ ] **Step 1: Move the web adapter**

```bash
git mv api/adapter/inbound/web adapter/inbound/web
```

Create `adapter/inbound/__init__.py` and `adapter/inbound/web/__init__.py` if needed (check if they were created in Task 4).

- [ ] **Step 2: Update all imports from `api.adapter.inbound.web.` to `adapter.inbound.web.`**

```bash
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/from api\.adapter\.inbound\.web\./from adapter.inbound.web./g; s/import api\.adapter\.inbound\.web\./import adapter.inbound.web./g'
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/"api\.adapter\.inbound\.web\./"adapter.inbound.web./g'
```

Also update `api/main.py` (soon to be `bootstrap/api.py`) which imports the routers:

```bash
find . -path ./.venv -prune -o -name '*.py' -print | xargs sed -i '' 's/from api\.adapter\.inbound/from adapter.inbound/g'
```

- [ ] **Step 3: Update `.importlinter`**

Replace `api.adapter.inbound.web` with `adapter.inbound.web` and `api.adapter.inbound` with `adapter.inbound`.

- [ ] **Step 4: Run full test suite + lint-imports**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(arch): move api/adapter/inbound/web/ to adapter/inbound/web/"
```

---

### Task 8: Move `api/main.py` to `bootstrap/api.py`

**Files:**
- Move: `api/main.py` → `bootstrap/api.py`
- Modify: `entrypoint.py`

- [ ] **Step 1: Move the file**

```bash
git mv api/main.py bootstrap/api.py
```

- [ ] **Step 2: Update entrypoint.py**

Change the uvicorn import path from `"api.main:app"` to `"bootstrap.api:app"`.

Also update `from api.main import ...` if referenced anywhere.

- [ ] **Step 3: Delete the now-empty `api/` directory**

```bash
rm -rf api
```

- [ ] **Step 4: Update `.importlinter`**

Remove `api` from `root_packages`. Update any contracts referencing `api`.

- [ ] **Step 5: Run full test suite + lint-imports**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor(arch): move api/main.py to bootstrap/api.py, eliminate api/"
```

---

### Task 9: Move `scheduler/` to `adapter/inbound/scheduler/` + `bootstrap/scheduler.py`

**Files:**
- Move: `scheduler/scheduler_loop.py` → `adapter/inbound/scheduler/scheduler_loop.py`
- Move: `scheduler/main.py` → `bootstrap/scheduler.py`
- Modify: `entrypoint.py`, imports

- [ ] **Step 1: Move adapter code**

```bash
mkdir -p adapter/inbound/scheduler
git mv scheduler/scheduler_loop.py adapter/inbound/scheduler/scheduler_loop.py
```

Create `adapter/inbound/scheduler/__init__.py`.

- [ ] **Step 2: Move composition root**

```bash
git mv scheduler/main.py bootstrap/scheduler.py
```

- [ ] **Step 3: Update imports in `bootstrap/scheduler.py`**

Change `from scheduler.scheduler_loop import SchedulerLoop` to `from adapter.inbound.scheduler.scheduler_loop import SchedulerLoop`.

- [ ] **Step 4: Update `entrypoint.py`**

Change `from scheduler.main import main as scheduler_main` to `from bootstrap.scheduler import main as scheduler_main`.

- [ ] **Step 5: Delete the now-empty `scheduler/` directory**

```bash
rm -rf scheduler
```

- [ ] **Step 6: Update `.importlinter`**

Remove `scheduler` from `root_packages`. Update contracts referencing `scheduler`.

- [ ] **Step 7: Update test imports**

Any test file importing from `scheduler.*` must be updated. Check `tests/scheduler/` directory — update imports to new paths.

```bash
find tests -name '*.py' -print | xargs sed -i '' 's/from scheduler\./from adapter.inbound.scheduler./g'
```

Move `tests/scheduler/` to `tests/adapter/inbound/scheduler/` to mirror the new layout.

```bash
mkdir -p tests/adapter/inbound/scheduler
git mv tests/scheduler/test_scheduler_loop.py tests/adapter/inbound/scheduler/test_scheduler_loop.py
rm -rf tests/scheduler
```

- [ ] **Step 8: Run full test suite + lint-imports**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(arch): move scheduler/ to adapter/inbound/scheduler/ + bootstrap/"
```

---

### Task 10: Move `outbox_publisher/` to `adapter/inbound/messaging/outbox/` + `bootstrap/messaging.py`

**Files:**
- Move: `outbox_publisher/publisher_loop.py` → `adapter/inbound/messaging/outbox/publisher_loop.py`
- Move: `outbox_publisher/main.py` → `bootstrap/messaging.py`
- Modify: `entrypoint.py`, imports

- [ ] **Step 1: Move adapter code**

```bash
mkdir -p adapter/inbound/messaging/outbox
git mv outbox_publisher/publisher_loop.py adapter/inbound/messaging/outbox/publisher_loop.py
```

Create `adapter/inbound/messaging/__init__.py` and `adapter/inbound/messaging/outbox/__init__.py`.

- [ ] **Step 2: Move composition root**

```bash
git mv outbox_publisher/main.py bootstrap/messaging.py
```

- [ ] **Step 3: Update imports in `bootstrap/messaging.py`**

Change `from outbox_publisher.publisher_loop import PublisherLoop` to `from adapter.inbound.messaging.outbox.publisher_loop import PublisherLoop`.

- [ ] **Step 4: Update `entrypoint.py`**

Change `from outbox_publisher.main import main as publisher_main` to `from bootstrap.messaging import main as publisher_main`.

- [ ] **Step 5: Delete the now-empty `outbox_publisher/` directory**

```bash
rm -rf outbox_publisher
```

- [ ] **Step 6: Update `.importlinter`**

Remove `outbox_publisher` from `root_packages`. Update contracts referencing `outbox_publisher`.

- [ ] **Step 7: Update test imports**

Move `tests/outbox_publisher/` to `tests/adapter/inbound/messaging/outbox/` if it exists. Update imports.

- [ ] **Step 8: Run full test suite + lint-imports**

Run: `UV_RUN pytest -v -k "not test_directory_structure" && UV_RUN lint-imports`
Expected: All PASS.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "refactor(arch): move outbox_publisher/ to adapter/inbound/messaging/outbox/ + bootstrap/"
```

---

### Task 11: Rewrite `.importlinter` for new structure

**Files:**
- Modify: `.importlinter`

Previous tasks did incremental updates. This task does a full rewrite to ensure consistency and clean up any leftover references.

- [ ] **Step 1: Write the complete new `.importlinter`**

```ini
[importlinter]
root_packages =
    adapter
    application
    base
    bootstrap
include_external_packages = True

[importlinter:contract:domain-core-isolation]
name = Domain core (entities, value objects) does not depend on application or adapter
type = forbidden
source_modules =
    application.domain.model
forbidden_modules =
    application.port
    application.exceptions
    application.service
    application.domain.service
    adapter
    bootstrap
    fastapi
    kubernetes

[importlinter:contract:application-isolation]
name = Application does not depend on adapter or bootstrap
type = forbidden
source_modules =
    application
forbidden_modules =
    adapter
    bootstrap
    fastapi
    kubernetes

[importlinter:contract:clean-architecture-layers]
name = Clean Architecture layer ordering
type = layers
layers =
    adapter.inbound.web
    application.service
    application.port
    application.domain.model

[importlinter:contract:inbound-outbound-separation]
name = Inbound adapter does not depend on outbound adapter
type = forbidden
source_modules =
    adapter.inbound
forbidden_modules =
    adapter.outbound

[importlinter:contract:outbound-inbound-separation]
name = Outbound adapter does not depend on inbound adapter
type = forbidden
source_modules =
    adapter.outbound
forbidden_modules =
    adapter.inbound

[importlinter:contract:configs-leaf]
name = Configs does not depend on bounded contexts
type = forbidden
source_modules =
    bootstrap.configs
forbidden_modules =
    adapter
    application

[importlinter:contract:base-isolation]
name = Base (DDD kernel) depends on nothing project-internal
type = forbidden
source_modules =
    base
forbidden_modules =
    application
    adapter
    bootstrap

[importlinter:contract:service-isolation]
name = Application service does not depend on adapter or framework
type = forbidden
source_modules =
    application.service
forbidden_modules =
    adapter
    bootstrap
    fastapi
    kubernetes

[importlinter:contract:adapter-no-bootstrap]
name = Adapter does not depend on bootstrap
type = forbidden
source_modules =
    adapter
forbidden_modules =
    bootstrap

[importlinter:contract:bootstrap-inbound-separation]
name = Bootstrap entry points are independent of each other's adapters
type = forbidden
source_modules =
    adapter.inbound.web
forbidden_modules =
    adapter.inbound.scheduler
    adapter.inbound.messaging

[importlinter:contract:bootstrap-dependencies-no-adapter-inbound]
name = Dependencies does not depend on inbound adapters
type = forbidden
source_modules =
    bootstrap.dependencies
forbidden_modules =
    adapter.inbound
```

- [ ] **Step 2: Run lint-imports**

Run: `UV_RUN lint-imports`
Expected: All contracts PASS. If any fail, fix the import violations.

- [ ] **Step 3: Commit**

```bash
git add .importlinter
git commit -m "refactor(arch): rewrite import-linter config for new hexagonal structure"
```

---

### Task 12: Update architecture guard tests

**Files:**
- Modify: `tests/architecture/test_service_structure.py`
- Modify: `tests/architecture/test_directory_structure.py`

- [ ] **Step 1: Update `test_service_structure.py` paths**

Change `SERVICE_DIR` from:
```python
SERVICE_DIR = Path(__file__).resolve().parents[2] / "core" / "application" / "service"
```
to:
```python
SERVICE_DIR = Path(__file__).resolve().parents[2] / "application" / "service"
```

Change imports from:
```python
from core.base.event_handler import EventHandler
from core.base.use_case import UseCase
```
to:
```python
from base.event_handler import EventHandler
from base.use_case import UseCase
```

- [ ] **Step 2: Run the architecture guard tests**

Run: `UV_RUN pytest tests/architecture/ -v`
Expected: All PASS — including the directory structure test from Task 1 (which should now be GREEN).

- [ ] **Step 3: Run the full test suite**

Run: `UV_RUN pytest -v`
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/architecture/
git commit -m "refactor(arch): update architecture guard tests for new directory structure"
```

---

### Task 13: Update `CLAUDE.md` and `tests/configs/` paths

**Files:**
- Modify: `CLAUDE.md` (project root)
- Modify: `tests/configs/` test imports

- [ ] **Step 1: Update CLAUDE.md backend structure diagram**

Update the Backend Structure section to reflect the new layout:

```
backend/
├── bootstrap/               # Composition roots
│   ├── configs/             # AppSettings, adapter enums
│   ├── dependencies/        # FastAPI dependency injection
│   ├── api.py               # API entry point
│   ├── scheduler.py         # Scheduler entry point
│   └── messaging.py         # Outbox publisher entry point
├── adapter/                 # Outermost ring
│   ├── inbound/
│   │   ├── web/             # FastAPI routes, API DTOs
│   │   ├── scheduler/       # Scheduler polling loop
│   │   └── messaging/
│   │       └── outbox/      # Outbox publisher polling loop
│   └── outbound/            # Repository implementations (SQL, K8s, in-memory)
├── application/             # Middle ring
│   ├── domain/model/        # Entities, Value Objects, Domain Events, Exceptions
│   ├── port/inbound/        # Use case interfaces + result types
│   ├── port/outbound/       # Repository interfaces
│   └── service/             # Use case implementations (application services)
├── base/                    # DDD shared kernel
├── entrypoint.py            # ROLE env var → api, scheduler, or outbox-publisher
└── tests/
```

Also update the Rules section:
- Replace `core/base/` with `base/`
- Replace `core/configs/` with `bootstrap/configs/`
- Replace references to `api/adapter/inbound/web/dto.py` with `adapter/inbound/web/...`
- Update scheduler references

- [ ] **Step 2: Update test config imports**

```bash
find tests/configs -name '*.py' -print | xargs sed -i '' 's/from core\.configs/from bootstrap.configs/g'
```

Verify these were already updated in Task 5. If so, skip this step.

- [ ] **Step 3: Move `tests/configs/` to `tests/bootstrap/configs/`**

```bash
mkdir -p tests/bootstrap/configs
git mv tests/configs/* tests/bootstrap/configs/
rm -rf tests/configs
```

Create `tests/bootstrap/__init__.py` and `tests/bootstrap/configs/__init__.py`.

- [ ] **Step 4: Run full test suite + all linters**

```bash
UV_RUN pytest -v && UV_RUN ruff check . && UV_RUN lint-imports
```

Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "docs(arch): update CLAUDE.md and test paths for new directory structure"
```

---

### Task 14: Final verification and cleanup

- [ ] **Step 1: Verify no stale `core.*` imports remain**

```bash
grep -r "from core\." --include="*.py" -l | grep -v __pycache__ | grep -v .venv
grep -r "import core\." --include="*.py" -l | grep -v __pycache__ | grep -v .venv
```

Expected: No output. If any files found, fix them.

- [ ] **Step 2: Verify no stale directory references**

```bash
# Should not exist
ls core/ 2>/dev/null && echo "ERROR: core/ still exists" || echo "OK: core/ removed"
ls api/ 2>/dev/null && echo "ERROR: api/ still exists" || echo "OK: api/ removed"
ls scheduler/ 2>/dev/null && echo "ERROR: scheduler/ still exists" || echo "OK: scheduler/ removed"
ls outbox_publisher/ 2>/dev/null && echo "ERROR: outbox_publisher/ still exists" || echo "OK: outbox_publisher/ removed"
ls dependencies/ 2>/dev/null && echo "ERROR: dependencies/ still exists" || echo "OK: dependencies/ removed"
```

- [ ] **Step 3: Run full verification suite**

```bash
UV_RUN pytest -v && UV_RUN ruff check . && UV_RUN lint-imports
```

Expected: All PASS with zero failures.

- [ ] **Step 4: Clean up any empty `__init__.py` or stale `__pycache__`**

```bash
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name '.import_linter_cache' -exec rm -rf {} +
```

- [ ] **Step 5: Final commit if any cleanup needed**

```bash
git add -A
git status
# Only commit if there are changes
git diff --cached --quiet || git commit -m "chore: clean up stale caches after directory restructure"
```
