# Outbound Gateway Structure Guard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure Gateway outbound ports into subdirectories with input/output VOs, rename `JobSubmission` → `SubmitJobRunInput`, and add architecture guard tests to enforce naming/structure/primitive-only constraints.

**Architecture:** Each Gateway gets its own subdirectory under `port/outbound/{aggregate}/` with `gateway.py`, optional `input.py`/`output.py`, and `__init__.py`. Repository and Store remain flat. An architecture test enforces structure, naming, base class, re-exports, and primitive-only imports on input/output files.

**Tech Stack:** Python 3, pytest, AST module, dataclasses

---

### Task 1: Write the architecture guard test (RED)

**Files:**
- Create: `src/table-maintenance/backend/tests/architecture/test_outbound_port_structure.py`

The test will fail initially because the current gateway files are flat (not in subdirectories).

- [ ] **Step 1: Create the architecture guard test**

```python
"""Guard tests for outbound port directory structure and naming conventions.

Outbound ports are grouped under port/outbound/{aggregate}/.

Three port types exist:
  - Repository: flat file, class extends Repository
  - Store: flat file, class extends Store
  - Gateway: subdirectory with gateway.py, optional input.py/output.py

Gateway subdirectory must contain:
  Required: __init__.py, gateway.py
  Optional: input.py, output.py

Naming convention for Gateway subdirectory {verb}_{noun}/:
  {Verb}{Noun}Gateway  in gateway.py
  {Verb}{Noun}Input    in input.py   (if present, primitive-only imports)
  {Verb}{Noun}Output   in output.py  (if present, primitive-only imports)

__init__.py must re-export all symbols via __all__.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from base.gateway import Gateway

OUTBOUND_PORT_DIR = (
    Path(__file__).resolve().parents[2] / "application" / "port" / "outbound"
)

AGGREGATE_GROUPS = ["catalog", "event_outbox", "job", "job_run"]

GATEWAY_REQUIRED_FILES = {"__init__.py", "gateway.py"}
GATEWAY_ALLOWED_FILES = {"__init__.py", "gateway.py", "input.py", "output.py"}

# Imports allowed in input.py / output.py (primitive-only constraint).
# These files must NOT import from application.domain or base (except base.value_object).
ALLOWED_INPUT_OUTPUT_IMPORT_PREFIXES = (
    "from __future__",
    "from dataclasses",
    "from typing",
    "from base.value_object",
    "import dataclasses",
    "import typing",
)


def _gateway_dirs() -> list[tuple[str, Path]]:
    """Return (aggregate, path) for all gateway subdirectories."""
    result: list[tuple[str, Path]] = []
    for group_name in AGGREGATE_GROUPS:
        group_dir = OUTBOUND_PORT_DIR / group_name
        if not group_dir.is_dir():
            continue
        for d in sorted(group_dir.iterdir()):
            if d.is_dir() and d.name != "__pycache__":
                result.append((group_name, d))
    return result


def _gateway_id(param: tuple[str, Path]) -> str:
    """Format a gateway entry as a readable pytest ID."""
    group, d = param
    return f"{group}/{d.name}"


def _pascal_case(name: str) -> str:
    """Convert 'submit_job_run' to 'SubmitJobRun'."""
    return "".join(word.capitalize() for word in name.split("_"))


def _exported_classes(module_path: str) -> list[str]:
    """Return class names defined in a module."""
    mod = importlib.import_module(module_path)
    return [
        name
        for name in dir(mod)
        if isinstance(getattr(mod, name), type) and not name.startswith("_")
    ]


def _parse_imports(file_path: Path) -> list[str]:
    """Return all import statements from a file as source lines."""
    source = file_path.read_text()
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(f"from {node.module}")
    return imports


# --- Rule 1: Only aggregate group directories exist ---


def test_only_aggregate_groups_in_outbound_port():
    """Verify that port/outbound/ contains only the expected aggregate group directories."""
    dirs = [
        d.name
        for d in OUTBOUND_PORT_DIR.iterdir()
        if d.is_dir() and d.name != "__pycache__"
    ]
    assert sorted(dirs) == sorted(AGGREGATE_GROUPS), (
        f"port/outbound/ must only contain aggregate groups {AGGREGATE_GROUPS}, found: {dirs}"
    )


# --- Rule 2: Gateway directory has required files ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_gateway_dir_has_required_files(gw_entry: tuple[str, Path]):
    """Verify that each gateway directory contains __init__.py and gateway.py."""
    _group, gw_dir = gw_entry
    actual_files = {
        f.name for f in gw_dir.iterdir() if f.is_file() and f.suffix == ".py"
    }
    missing = GATEWAY_REQUIRED_FILES - actual_files
    assert missing == set(), f"{gw_dir.name}/ is missing: {missing}"


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_gateway_dir_has_no_extra_files(gw_entry: tuple[str, Path]):
    """Verify that each gateway directory contains no unexpected files."""
    _group, gw_dir = gw_entry
    actual_files = {
        f.name for f in gw_dir.iterdir() if f.is_file() and f.suffix == ".py"
    }
    extra = actual_files - GATEWAY_ALLOWED_FILES
    assert extra == set(), f"{gw_dir.name}/ has unexpected files: {extra}"


# --- Rule 3: gateway.py class naming and base class ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_gateway_class_naming(gw_entry: tuple[str, Path]):
    """Verify that gateway.py exports {Verb}{Noun}Gateway extending Gateway."""
    group, gw_dir = gw_entry
    prefix = _pascal_case(gw_dir.name)
    expected = f"{prefix}Gateway"
    module = f"application.port.outbound.{group}.{gw_dir.name}.gateway"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{gw_dir.name}/gateway.py must export '{expected}', found: {classes}"
    )


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_gateway_extends_base(gw_entry: tuple[str, Path]):
    """Verify that the Gateway class extends base.gateway.Gateway."""
    group, gw_dir = gw_entry
    prefix = _pascal_case(gw_dir.name)
    expected = f"{prefix}Gateway"
    module = f"application.port.outbound.{group}.{gw_dir.name}.gateway"
    mod = importlib.import_module(module)
    cls = getattr(mod, expected)
    assert issubclass(cls, Gateway), (
        f"{expected} must extend Gateway, bases: {[b.__name__ for b in cls.__mro__]}"
    )


# --- Rule 4: input.py class naming (if exists) ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_input_class_naming(gw_entry: tuple[str, Path]):
    """Verify that input.py exports {Verb}{Noun}Input (if present)."""
    group, gw_dir = gw_entry
    input_file = gw_dir / "input.py"
    if not input_file.exists():
        pytest.skip("No input.py")
    prefix = _pascal_case(gw_dir.name)
    expected = f"{prefix}Input"
    module = f"application.port.outbound.{group}.{gw_dir.name}.input"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{gw_dir.name}/input.py must export '{expected}', found: {classes}"
    )


# --- Rule 5: output.py class naming (if exists) ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_output_class_naming(gw_entry: tuple[str, Path]):
    """Verify that output.py exports {Verb}{Noun}Output (if present)."""
    group, gw_dir = gw_entry
    output_file = gw_dir / "output.py"
    if not output_file.exists():
        pytest.skip("No output.py")
    prefix = _pascal_case(gw_dir.name)
    expected = f"{prefix}Output"
    module = f"application.port.outbound.{group}.{gw_dir.name}.output"
    classes = _exported_classes(module)
    assert expected in classes, (
        f"{gw_dir.name}/output.py must export '{expected}', found: {classes}"
    )


# --- Rule 6: input.py / output.py primitive-only imports ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_input_primitive_only(gw_entry: tuple[str, Path]):
    """Verify that input.py does not import domain or base types (except ValueObject)."""
    _group, gw_dir = gw_entry
    input_file = gw_dir / "input.py"
    if not input_file.exists():
        pytest.skip("No input.py")
    imports = _parse_imports(input_file)
    violations = [
        imp for imp in imports
        if not any(imp.startswith(prefix) for prefix in ALLOWED_INPUT_OUTPUT_IMPORT_PREFIXES)
    ]
    assert violations == [], (
        f"{gw_dir.name}/input.py has non-primitive imports: {violations}"
    )


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_output_primitive_only(gw_entry: tuple[str, Path]):
    """Verify that output.py does not import domain or base types (except ValueObject)."""
    _group, gw_dir = gw_entry
    output_file = gw_dir / "output.py"
    if not output_file.exists():
        pytest.skip("No output.py")
    imports = _parse_imports(output_file)
    violations = [
        imp for imp in imports
        if not any(imp.startswith(prefix) for prefix in ALLOWED_INPUT_OUTPUT_IMPORT_PREFIXES)
    ]
    assert violations == [], (
        f"{gw_dir.name}/output.py has non-primitive imports: {violations}"
    )


# --- Rule 7: __init__.py re-exports all symbols ---


@pytest.mark.parametrize("gw_entry", _gateway_dirs(), ids=_gateway_id)
def test_init_reexports_all_symbols(gw_entry: tuple[str, Path]):
    """Verify that __init__.py re-exports Gateway, Input, Output via __all__."""
    group, gw_dir = gw_entry
    prefix = _pascal_case(gw_dir.name)
    module = f"application.port.outbound.{group}.{gw_dir.name}"
    mod = importlib.import_module(module)
    exported = set(getattr(mod, "__all__", []))

    # Gateway is always required
    assert f"{prefix}Gateway" in exported, (
        f"{gw_dir.name}/__init__.py must re-export '{prefix}Gateway' in __all__"
    )
    # Input is required if input.py exists
    if (gw_dir / "input.py").exists():
        assert f"{prefix}Input" in exported, (
            f"{gw_dir.name}/__init__.py must re-export '{prefix}Input' in __all__"
        )
    # Output is required if output.py exists
    if (gw_dir / "output.py").exists():
        assert f"{prefix}Output" in exported, (
            f"{gw_dir.name}/__init__.py must re-export '{prefix}Output' in __all__"
        )
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/architecture/test_outbound_port_structure.py -v`

Expected: FAIL — no gateway subdirectories exist yet, `_gateway_dirs()` returns empty list, and `test_only_aggregate_groups_in_outbound_port` should pass since groups already exist. The parametrized tests will be "no tests ran" (0 collected) since there are no gateway dirs.

Actually the test should still pass vacuously (no gateway dirs = no parametrized cases). We need to verify the test file itself is valid and imports work. The real failures come after Task 2 restructures but has naming mismatches.

---

### Task 2: Restructure `submit_job_run` gateway into subdirectory

**Files:**
- Create: `src/table-maintenance/backend/application/port/outbound/job_run/submit_job_run/__init__.py`
- Create: `src/table-maintenance/backend/application/port/outbound/job_run/submit_job_run/gateway.py`
- Create: `src/table-maintenance/backend/application/port/outbound/job_run/submit_job_run/input.py`
- Delete: `src/table-maintenance/backend/application/port/outbound/job_run/submit_job_run_gateway.py`
- Delete: `src/table-maintenance/backend/application/port/outbound/job_run/job_submission.py`
- Modify: `src/table-maintenance/backend/application/port/outbound/job_run/__init__.py`

- [ ] **Step 1: Create `submit_job_run/gateway.py`**

```python
"""Define the SubmitJobRunGateway port interface."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from base.gateway import Gateway

if TYPE_CHECKING:
    from application.port.outbound.job_run.submit_job_run.input import SubmitJobRunInput


class SubmitJobRunGateway(Gateway):
    """Gateway for submitting a job to an external execution system.

    The gateway performs a side-effect (e.g. creating a SparkApplication
    in Kubernetes). It does not create domain entities — that responsibility
    belongs to the application service layer.
    """

    @abstractmethod
    def submit(self, submission: SubmitJobRunInput) -> None:
        """Submit the job for execution in the external system."""
        ...
```

- [ ] **Step 2: Create `submit_job_run/input.py`**

Rename `JobSubmission` → `SubmitJobRunInput`. Keep primitive-only fields.

```python
"""Define the SubmitJobRunInput value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.value_object import ValueObject


@dataclass(frozen=True)
class SubmitJobRunInput(ValueObject):
    """Encapsulates all information needed to submit a job to an external executor.

    Uses only primitive types so that adapter implementations need zero
    domain imports.
    """

    run_id: str
    job_id: str
    job_type: str
    catalog: str
    table: str
    job_config: dict
    driver_memory: str
    executor_memory: str
    executor_instances: int
    cron_expression: str | None
```

- [ ] **Step 3: Create `submit_job_run/__init__.py`**

```python
"""SubmitJobRun gateway port."""

from application.port.outbound.job_run.submit_job_run.gateway import SubmitJobRunGateway
from application.port.outbound.job_run.submit_job_run.input import SubmitJobRunInput

__all__ = ["SubmitJobRunGateway", "SubmitJobRunInput"]
```

- [ ] **Step 4: Update `job_run/__init__.py`**

```python
"""JobRun repository and gateway ports."""

from application.port.outbound.job_run.submit_job_run import SubmitJobRunGateway, SubmitJobRunInput
from application.port.outbound.job_run.job_runs_repo import JobRunsRepo

__all__ = ["JobRunsRepo", "SubmitJobRunGateway", "SubmitJobRunInput"]
```

- [ ] **Step 5: Delete old flat files**

Delete:
- `src/table-maintenance/backend/application/port/outbound/job_run/submit_job_run_gateway.py`
- `src/table-maintenance/backend/application/port/outbound/job_run/job_submission.py`

- [ ] **Step 6: Update `port/outbound/__init__.py`**

```python
"""Outbound port interfaces (repositories, stores, gateways)."""

from application.port.outbound.catalog import ReadCatalogGateway
from application.port.outbound.job import JobsRepo
from application.port.outbound.job_run import SubmitJobRunGateway, JobRunsRepo, SubmitJobRunInput

__all__ = ["ReadCatalogGateway", "JobRunsRepo", "JobsRepo", "SubmitJobRunGateway", "SubmitJobRunInput"]
```

---

### Task 3: Update all `JobSubmission` → `SubmitJobRunInput` references

**Files to modify** (update import paths and class name):

Source files:
- `src/table-maintenance/backend/application/service/job_run/submit_job_run.py`
  - Line 11: `from application.port.outbound.job_run.job_submission import JobSubmission` → `from application.port.outbound.job_run.submit_job_run.input import SubmitJobRunInput`
  - Line 28: `submission = JobSubmission(` → `submission = SubmitJobRunInput(`
- `src/table-maintenance/backend/adapter/outbound/job_run/k8s/submit_job_run_k8s_gateway.py`
  - Line 20: `from application.port.outbound.job_run.job_submission import JobSubmission` → `from application.port.outbound.job_run.submit_job_run.input import SubmitJobRunInput`
  - Line 31: `def submit(self, submission: JobSubmission)` → `def submit(self, submission: SubmitJobRunInput)`
- `src/table-maintenance/backend/adapter/outbound/job_run/k8s/manifest.py`
  - Line 11: `from application.port.outbound.job_run.job_submission import JobSubmission` → `from application.port.outbound.job_run.submit_job_run.input import SubmitJobRunInput`
  - Lines 38, 51, 83: `JobSubmission` → `SubmitJobRunInput`
- `src/table-maintenance/backend/adapter/outbound/job_run/submit_job_run_in_memory_gateway.py`
  - Line 10: `from application.port.outbound.job_run.job_submission import JobSubmission` → `from application.port.outbound.job_run.submit_job_run.input import SubmitJobRunInput`
  - Lines 18, 20: `JobSubmission` → `SubmitJobRunInput`

- [ ] **Step 1: Update application service**

In `submit_job_run.py`:
- Change import from `application.port.outbound.job_run.job_submission` to `application.port.outbound.job_run.submit_job_run.input`
- Change `JobSubmission` → `SubmitJobRunInput` everywhere

- [ ] **Step 2: Update k8s gateway adapter**

In `submit_job_run_k8s_gateway.py`:
- Change import path and class name `JobSubmission` → `SubmitJobRunInput`

- [ ] **Step 3: Update k8s manifest builder**

In `manifest.py`:
- Change import path and class name `JobSubmission` → `SubmitJobRunInput` (4 occurrences)

- [ ] **Step 4: Update in-memory gateway adapter**

In `submit_job_run_in_memory_gateway.py`:
- Change import path and class name `JobSubmission` → `SubmitJobRunInput` (3 occurrences)

---

### Task 4: Update all `submit_job_run_gateway` import paths

**Files to modify** (old flat module path → new subdirectory path):

Old: `application.port.outbound.job_run.submit_job_run_gateway`
New: `application.port.outbound.job_run.submit_job_run.gateway`

Source files:
- `src/table-maintenance/backend/adapter/outbound/job_run/k8s/submit_job_run_k8s_gateway.py` (line 14)
- `src/table-maintenance/backend/adapter/outbound/job_run/submit_job_run_in_memory_gateway.py` (line 7)
- `src/table-maintenance/backend/application/service/job_run/submit_job_run.py` (line 14-15)
- `src/table-maintenance/backend/bootstrap/dependencies/repos.py` (line 34-35)

- [ ] **Step 1: Update all four source files**

Change every `from application.port.outbound.job_run.submit_job_run_gateway import SubmitJobRunGateway` to `from application.port.outbound.job_run.submit_job_run.gateway import SubmitJobRunGateway`.

---

### Task 5: Update all test file references

**Test files to modify** (import paths for both `JobSubmission` → `SubmitJobRunInput` and `submit_job_run_gateway` → `submit_job_run.gateway`):

- `tests/test_error_executor_failure.py` (lines 27-28, 41)
- `tests/test_event_chain_publish.py` (line 34, 168)
- `tests/application/port/outbound/job_run/test_job_submission.py` → rename to `tests/application/port/outbound/job_run/test_submit_job_run_input.py`
- `tests/application/port/outbound/job_run/test_submit_job_run_gateway.py` (line 7)
- `tests/adapter/outbound/job_run/k8s/test_manifest.py` (lines 5, 20, 34)
- `tests/adapter/outbound/job_run/k8s/test_submit_job_run_k8s_gateway.py` (lines 9-10, 25, 39)
- `tests/adapter/outbound/job_run/test_submit_job_run_in_memory_gateway.py` (lines 6-7, 10, 24)
- `tests/application/service/job_run/test_submit_job_run.py` (lines 9, 41)

- [ ] **Step 1: Rename and update `test_job_submission.py`**

Rename to `test_submit_job_run_input.py`. Update all `JobSubmission` → `SubmitJobRunInput` and import path to `application.port.outbound.job_run.submit_job_run.input`.

- [ ] **Step 2: Update `test_submit_job_run_gateway.py`**

Change import from `application.port.outbound.job_run.submit_job_run_gateway` to `application.port.outbound.job_run.submit_job_run.gateway`.

- [ ] **Step 3: Update remaining test files**

Update import paths and class names in all other test files listed above.

---

### Task 6: Restructure `read_catalog` gateway into subdirectory

**Files:**
- Create: `src/table-maintenance/backend/application/port/outbound/catalog/read_catalog/__init__.py`
- Create: `src/table-maintenance/backend/application/port/outbound/catalog/read_catalog/gateway.py`
- Delete: `src/table-maintenance/backend/application/port/outbound/catalog/read_catalog_gateway.py`
- Modify: `src/table-maintenance/backend/application/port/outbound/catalog/__init__.py`

- [ ] **Step 1: Create `read_catalog/gateway.py`**

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

- [ ] **Step 2: Create `read_catalog/__init__.py`**

```python
"""ReadCatalog gateway port."""

from application.port.outbound.catalog.read_catalog.gateway import ReadCatalogGateway

__all__ = ["ReadCatalogGateway"]
```

- [ ] **Step 3: Update `catalog/__init__.py`**

```python
"""Catalog gateway port."""

from application.port.outbound.catalog.read_catalog import ReadCatalogGateway

__all__ = ["ReadCatalogGateway"]
```

- [ ] **Step 4: Delete old flat file**

Delete: `src/table-maintenance/backend/application/port/outbound/catalog/read_catalog_gateway.py`

---

### Task 7: Update all `read_catalog_gateway` import paths

**Files to modify:**

Old: `application.port.outbound.catalog.read_catalog_gateway`
New: `application.port.outbound.catalog.read_catalog.gateway`

Source files:
- `src/table-maintenance/backend/adapter/outbound/catalog/read_catalog_iceberg_gateway.py` (line 17)
- `src/table-maintenance/backend/application/service/catalog/get_table.py` (line 16-17)
- `src/table-maintenance/backend/application/service/catalog/list_tags.py` (line 15-16)
- `src/table-maintenance/backend/application/service/catalog/list_branches.py` (line 17-18)
- `src/table-maintenance/backend/application/service/catalog/list_namespaces.py` (line 18-19)
- `src/table-maintenance/backend/application/service/catalog/list_snapshots.py` (line 19-20)
- `src/table-maintenance/backend/application/service/catalog/list_tables.py` (line 12-13)
- `src/table-maintenance/backend/bootstrap/dependencies/catalog.py` (line 12)
- `src/table-maintenance/backend/bootstrap/dependencies/use_cases.py` (line 49-50)

Test files:
- `tests/adapter/outbound/catalog/test_read_catalog_iceberg_gateway.py` (line 13)
- `tests/application/port/outbound/catalog/test_read_catalog_gateway.py` (line 9)

- [ ] **Step 1: Update all source files**

Change every `from application.port.outbound.catalog.read_catalog_gateway import ReadCatalogGateway` to `from application.port.outbound.catalog.read_catalog.gateway import ReadCatalogGateway`.

- [ ] **Step 2: Update all test files**

Same import path change in test files.

---

### Task 8: Run all tests and verification

- [ ] **Step 1: Run architecture tests**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest tests/architecture/test_outbound_port_structure.py -v`

Expected: All tests PASS.

- [ ] **Step 2: Run full test suite**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`

Expected: All tests PASS.

- [ ] **Step 3: Run linting**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ruff check .`

Expected: No errors.

- [ ] **Step 4: Run import linter**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend lint-imports`

Expected: All contracts KEPT.

- [ ] **Step 5: Run type checker**

Run: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend ty check`

Expected: No errors.

- [ ] **Step 6: Commit**

```bash
git add -A src/table-maintenance/backend/
git commit -m "refactor(outbound): restructure gateway ports into subdirectories with architecture guard

- Move each Gateway into its own subdirectory with gateway.py, optional input.py/output.py
- Rename JobSubmission → SubmitJobRunInput (primitive-only VO)
- Add test_outbound_port_structure.py to enforce naming, structure, and primitive-only constraints
- Update all import paths across source and test files"
```

---

### Task 9: Update CLAUDE.md with new convention

- [ ] **Step 1: Update the Backend Structure section in CLAUDE.md**

Add the gateway subdirectory structure to the outbound port documentation, after the existing `Gateway` row in the naming convention table.

Add to the "Outbound Port & Adapter Naming Convention" section:

```markdown
**Gateway directory structure** (under `port/outbound/{aggregate}/`):
\```
{verb}_{noun}/
├── __init__.py       # re-export all symbols
├── gateway.py        # {Verb}{Noun}Gateway (extends Gateway)
├── input.py          # {Verb}{Noun}Input (optional, primitive-only)
└── output.py         # {Verb}{Noun}Output (optional, primitive-only)
\```

Input/output files must only use primitive types (`str`, `int`, `float`, `bool`, `dict`, `list`, `None`). They may import `base.value_object.ValueObject` but nothing from `application.domain` or other `base.*` modules.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add gateway subdirectory structure convention to CLAUDE.md"
```
