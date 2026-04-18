# Enable Pydocstyle (D Rules) in Ruff

## Goal

Enable the `D` (pydocstyle) rule set in `ruff.toml` and add Google-style
docstrings to all public modules, classes, functions, methods, and packages in
the `table-maintenance/backend` codebase — including tests.

## Ruff Configuration

- Add `"D"` to `lint.select` in `ruff.toml`
- Add `D203` and `D213` to `lint.ignore` (conflict with D211 and D212)
- Add `[lint.pydocstyle]` section with `convention = "google"`

### Incompatible Rule Resolutions

| Keep    | Ignore  | Reason                                      |
|---------|---------|---------------------------------------------|
| D211    | D203    | No blank line before class docstring         |
| D212    | D213    | Summary on same line as opening `"""`        |

## Docstring Style Guide

All docstrings follow the Google convention:

- **One-line summary** on same line as opening `"""`, imperative mood
  ("Create a job" not "Creates a job")
- **Blank line** between summary and body for multi-line docstrings
- **`Args:`** section when parameters are non-obvious (skip `self`, skip
  self-explanatory parameters like `job_id: JobId`)
- **`Returns:`** section when return value isn't obvious from name/type
- **`Raises:`** section when the function explicitly raises exceptions

### Per-construct rules

| Construct          | Rule | Guideline                                                |
|--------------------|------|----------------------------------------------------------|
| Module (`D100`)    |      | One-line summary describing the module's primary export  |
| Package (`D104`)   |      | One-line summary in `__init__.py` of the package purpose |
| Class (`D101`)     |      | Summary describing the class's responsibility            |
| Function (`D103`)  |      | Summary + `Args:`/`Returns:`/`Raises:` when non-obvious  |
| Method (`D102`)    |      | Same as function                                         |
| `__init__` (`D107`)|      | Skip for simple injection/dataclass; add for complex init|
| Magic method (`D105`)|    | Brief summary of the override's purpose                  |

### Test-specific rules

- **Test modules**: one-line summary, e.g. `"""Tests for SqlJobsRepo."""`
- **Test classes**: one-line summary, e.g. `"""Verify job creation and retrieval."""`
- **Test functions**: one-line summary describing the assertion,
  e.g. `"""Return empty list when no jobs exist."""`
- **Fixtures**: one-line summary of what the fixture provides,
  e.g. `"""Provide an in-memory SQLite engine."""`
- No `Args:`/`Returns:` for test functions

## Execution Strategy: Layer-by-layer

Each step produces one atomic commit. Ruff `per-file-ignores` suppresses
uncovered layers until their turn.

| #  | Commit Scope                          | Description                              |
|----|---------------------------------------|------------------------------------------|
| 1  | `ruff.toml` config                    | Enable `D`, add ignores, add per-file suppressions for all dirs |
| 2  | `base/`                               | Shared kernel (mostly done already)      |
| 3  | `application/domain/`                 | Entities, value objects, events, exceptions |
| 4  | `application/port/`                   | Use case & repository interfaces         |
| 5  | `application/service/`                | Use case implementations                 |
| 6  | `adapter/outbound/`                   | Repository & executor implementations    |
| 7  | `adapter/inbound/`                    | FastAPI routes, DTOs                     |
| 8  | `configs/` + `dependencies/` + `shared/` | Cross-cutting infrastructure          |
| 9  | `tests/`                              | All test files                           |
| 10 | Config cleanup                        | Remove all `per-file-ignores` suppressions |

## Validation

Each commit must pass:
- `ruff check .`
- `ruff format .`
- `pytest -v`
- `lint-imports`
