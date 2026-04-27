# Outbound Gateway Structure Guard

**Date:** 2026-04-27
**Status:** Approved

## Problem

Gateway outbound ports lack structural enforcement. The `primitive-only` constraint on Gateway input/output VOs (e.g., `JobSubmission`) is documented in docstrings but not enforced by any automated test or import-linter rule. Import-linter cannot catch this because both `application.port.outbound` and `application.domain.model` live under `application`.

## Design

### 1. Gateway Directory Structure

Each Gateway gets its own subdirectory under `port/outbound/{aggregate}/`:

```
port/outbound/{aggregate}/
├── {aggregate}s_repo.py          # Repository (flat)
├── {noun}_store.py               # Store (flat)
└── {verb}_{noun}/                # Gateway (subdirectory)
    ├── __init__.py               # re-export all symbols
    ├── gateway.py                # {Verb}{Noun}Gateway
    ├── input.py (optional)       # {Verb}{Noun}Input, primitive only
    └── output.py (optional)      # {Verb}{Noun}Output, primitive only
```

**Examples:**
- `port/outbound/job_run/submit_job_run/gateway.py` → `SubmitJobRunGateway`
- `port/outbound/job_run/submit_job_run/input.py` → `SubmitJobRunInput`
- `port/outbound/catalog/read_catalog/gateway.py` → `ReadCatalogGateway`

### 2. Architecture Test Rules

Test file: `tests/architecture/test_outbound_port_structure.py`

**Rule 1: Gateway directory has required files.**
- `__init__.py` and `gateway.py` must exist.
- Only allowed files: `__init__.py`, `gateway.py`, `input.py`, `output.py`.

**Rule 2: gateway.py naming.**
- Must export a class named `{Verb}{Noun}Gateway`.
- Class must be a subclass of `base.gateway.Gateway`.

**Rule 3: input.py naming (if exists).**
- Must export a class named `{Verb}{Noun}Input`.

**Rule 4: output.py naming (if exists).**
- Must export a class named `{Verb}{Noun}Output`.

**Rule 5: input.py / output.py primitive-only constraint.**
- These files must NOT import from `application.domain` or `base.*` (except `base.value_object`).
- Enforced via AST inspection of import statements.

**Rule 6: `__init__.py` re-exports.**
- Must re-export all symbols (Gateway, and Input/Output if they exist) via `__all__`.

### 3. Refactoring Required

| Before | After |
|--------|-------|
| `job_run/submit_job_run_gateway.py` | `job_run/submit_job_run/gateway.py` |
| `job_run/job_submission.py` | `job_run/submit_job_run/input.py` |
| `JobSubmission` class | `SubmitJobRunInput` class |
| `catalog/read_catalog_gateway.py` | `catalog/read_catalog/gateway.py` |

### 4. Scope

- **Gateway only.** Repository and Store remain flat files — they work directly with domain entities and don't need input/output VOs.
- **Primitive-only applies to input.py/output.py only.** The gateway.py itself may reference domain types in its method signatures.
