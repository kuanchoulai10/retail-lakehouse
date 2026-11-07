# Backend Ruff Rules and Frontend Move Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every rule in the root `ruff.toml` apply to `src/data-platform/backend`, fix every violation, and move `src/console` to `src/data-platform/frontend`, with no change in runtime behavior.

**Architecture:**
- Since 963343d (2026-04-12), the backend's own `[tool.ruff]` table in `pyproject.toml` has shadowed the root `ruff.toml`. Ruff uses only the nearest config and does not merge them.
- The backend config will `extend` the root config instead.
- The commits that turn the rules on first add a temporary per-directory ignore list. Later tasks shrink that list to empty, and a final guard test keeps it empty.
- The console move is path-only. Runtime names stay `console`.

**Tech Stack:** ruff 0.15.8 (via `uv run` and pre-commit), Python 3.14, pytest, React + Vite (console), wave-25 Helm chart.

**Spec:** none written. The decisions come from the owner in chat on 2026-11-07:
- "要繼承根目錄規則 … 全部的規則都要生效在 backend 裡面" (inherit the root rules; every rule must take effect in the backend).
- Move the console to `src/data-platform/frontend`.
- Keep the pod / runtime name `console`.
- Stop before pushing and notify the owner.

The plan is the binding authority here.

## Global Constraints

- Commits go on `main`. No branch, no worktree, no push. Stage files by explicit path. Never stage `docs/architecture.excalidraw.svg` or anything under `src/*/temp/`.
- Conventional commits: lowercase subject, every line ≤ 100 chars, message ends with a blank line and then `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.
- Every commit passes the four project commands from the backend:
  - `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest -v`
  - `… ty check`
  - `… ruff check .`
  - `… lint-imports`

  Pre-commit hooks run; never use `--no-verify`. The baseline is 1382 passed, 16 skipped; the test count must not drop.
- The root `ruff.toml` is not edited. Backend-only settings go in the backend `[tool.ruff]` table and may only add knowledge: isort first-party packages, and runtime-evaluated decorators or base classes. They must not ignore or deselect a rule, except for the temporary list below.
- No `# noqa` is added unless the line truly cannot comply. Each one names its rule code and gets a one-line reason in the task report. Pre-existing `# noqa: F401` re-export markers stay.
- No behavior change: no logic edits and no renamed public names. Docstrings, import placement, line wrapping and the fixes the rules ask for (for example `zip(..., strict=True)` where lengths are equal by construction) are the only edits. A rule fix that would change behavior gets reported, not applied.
- Docstrings follow the Google convention (root `[lint.pydocstyle] convention = "google"`). They say what the thing does or, for tests, which behavior is checked, in the style of `scripts/tests/test_check_k8s_labels.py` ("""A Deployment that follows the standard passes."""). Never write empty restatements such as `"""Test foo."""` or `"""Init."""`.
- No `cd`. Use `uv run`. `rm -rf` is blocked. Temporary files go in `/Users/kcl/.claude/jobs/ffac9ee8/tmp`.

## Fixed names

| Thing | Value |
|---|---|
| Backend ruff table | `[tool.ruff]` with `extend = "../../../ruff.toml"` and `[tool.ruff.lint.isort] known-first-party = ["base", "bootstrap", "context", "tests"]`. Optional `[tool.ruff.lint.flake8-type-checking]` runtime-evaluated additions (Task 2). |
| Temporary ignore list | `[tool.ruff.lint] extend-per-file-ignores`, with keys `"base/**"`, `"bootstrap/**"`, `"context/**"`, `"entrypoint.py"`, `"tests/**"`. Each value lists the codes still violated under that key. Task 1 creates it; Tasks 2–3 empty it; Task 3 deletes the table. |
| Guard test | `tests/architecture/test_ruff_config.py` |
| Frontend path | `src/data-platform/frontend/`, the former `src/console/`. Image, Deployment, Service, HTTPRoute, `/console` path and labels stay `console`. |

## Review Focus

- **TYPE_CHECKING moves that break runtime.** Every module has `from __future__ import annotations`, and the TC00x rules want type-only imports moved under `if TYPE_CHECKING:`. Several readers evaluate annotations at runtime:
  - the Temporal data converter (workflow, activity and signal parameter types, and dataclass payloads);
  - FastAPI route signatures and the DTOs they use;
  - pydantic models and settings;
  - `dataclasses` fields read through `typing.get_type_hints`.

  Moving one of those imports fails only at runtime. Task 2 keeps such imports at runtime. It does this by adding the decorators or base classes to `runtime-evaluated-decorators` / `runtime-evaluated-base-classes`, not with `noqa`. Task 5's e2e is the proof that payloads still round-trip.
- **Formatter line length 88 → 120.** Inheriting the root `line-length = 120` reflows 234 files. The reflow belongs in its own commit with no other edits, so it can be reviewed as layout only.
- **Import sorting misplaces `context`.** If `context` is not known as first-party, isort sorts it as third-party. `from context…` then lands above `from bootstrap…` with a blank line between. Task 1 sets `known-first-party` before the first autofix.
- **The root `tests/*` per-file-ignore does not match backend tests.** Root patterns resolve against the root directory, so backend tests get no FA100 exemption. That is accepted: backend modules already have `from __future__ import annotations`. Report the case if FA100 fires anyway.
- **Console move leftovers.** Check for relative paths inside the console (`tsconfig.json`, `vite.config.ts`, `components.json`, `eslint.config.js`, `.dockerignore`, `Dockerfile`) and for ignored build output (`node_modules`, `dist`) still sitting at the old path.

---

### Task 1: Inherit the root ruff config, sort imports, reflow

**Files:**
- Modify: `src/data-platform/backend/pyproject.toml` (the `[tool.ruff…]` tables)
- Modify (generated by ruff only): any backend `.py` file

**Interfaces:** Produces the backend ruff table and the temporary ignore list (Fixed names). Tasks 2–3 shrink the list.

- [ ] **Step 1:** Record the baseline:
  - `uv run --directory <repo> ruff check --config ruff.toml --no-fix --statistics src/data-platform/backend` (expect about 1560 violations, 268 of them I001);
  - the pytest count (expect 1382 passed, 16 skipped).
- [ ] **Step 2: Rewrite the backend ruff table.** Use the backend ruff table from Fixed names. Confirm the settings with `ruff check --show-settings` from the backend: `line_length = 120`, the root `select` list, `fix = true`, `known-first-party` includes `context`.
- [ ] **Step 3: Commit A, layout only.** Run `ruff format .` from the backend. Commit it as `style(backend): reflow to the root ruff line length`. The diff must be whitespace and wrapping only: `git diff --ignore-all-space --stat` should show only re-wrapped lines. Run the four commands before committing; if `ruff check` fails because of not-yet-listed rules, do Step 4 first and combine the two steps into commit B.
- [ ] **Step 4: Commit B, rules on.**
  1. Run `ruff check --fix .` (I001 and W). Inspect a sample of the sorted files: `context`, `base`, `bootstrap` and `tests` imports must form one first-party block after the third-party block.
  2. List every code that still fails under each key in `extend-per-file-ignores`. Get them from `ruff check --statistics` per directory.
  3. Commit as `build(backend): apply the root ruff rules to the backend`. The body lists the temporary ignore list and says that Tasks 2–3 empty it.
- [ ] **Step 5: Verify.**
  - The four commands pass.
  - The test count is unchanged.
  - `ruff check --no-fix .` from the backend is clean.
  - `ruff check --config ruff.toml` from the repo root on the backend shows the same code set as the ignore list.

### Task 2: Fix the production code (`base`, `bootstrap`, `context`, `entrypoint.py`)

**Files:**
- Modify: backend `.py` files outside `tests/` (about 383 violations)
- Modify: the backend ruff table (remove the four non-test keys; optionally add runtime-evaluated settings)

**Interfaces:**
- Consumes: the Task 1 ignore list.
- Produces: an ignore list holding only `"tests/**"`.

- [ ] **Step 1:** Remove the `"base/**"`, `"bootstrap/**"`, `"context/**"` and `"entrypoint.py"` keys. `ruff check --no-fix .` must now list only production-code violations. Record the counts per code.
- [ ] **Step 2: TC00x.**
  - Identify the runtime-evaluated annotations named in Review Focus:
    - Temporal workflow and activity definitions and their payload dataclasses (`adapter/hybrid/temporal/contracts`, `inbound`);
    - FastAPI routers and DTOs (`adapter/inbound/web`);
    - pydantic settings (`bootstrap/configs`).
  - For those, add the decorators or base classes to `[tool.ruff.lint.flake8-type-checking]`: `runtime-evaluated-decorators` (for example `temporalio.workflow.defn`, `temporalio.activity.defn`) and `runtime-evaluated-base-classes` (extend the root's pydantic entries with any project base the converter reads).
  - Move only the remaining imports under `TYPE_CHECKING`.
  - In the report, state for each runtime-evaluated entry why it is needed.
- [ ] **Step 3: Fix the remaining production violations** (D1xx docstrings, E501, B, PL, A, UP, ERA, PYI) under the Global Constraints rules on docstrings, `noqa` and behavior.
- [ ] **Step 4: Verify.**
  - The four commands pass with an unchanged test count.
  - The architecture tests pass. They include `test_temporal_workflow_sandbox.py`, `test_temporal_workflow_determinism.py` and the boundary tests.
  - The import smoke check passes: `uv run --directory src/data-platform/backend python -c "import entrypoint, bootstrap.api, bootstrap.worker, bootstrap.event_consumer, bootstrap.migrate"`.
- [ ] **Step 5: Commit** as `style(backend): satisfy the root ruff rules in production code`. Split it into one commit per rule family if the diff is easier to review that way.

### Task 3: Fix the tests and close the ignore list

**Files:**
- Modify: backend `tests/**/*.py` (about 1178 violations, mostly D103 / D102 / D104 / D100)
- Modify: the backend ruff table (delete `extend-per-file-ignores`)
- Create: `src/data-platform/backend/tests/architecture/test_ruff_config.py`

**Interfaces:** Consumes the Task 2 ignore list, which holds only `"tests/**"`.

- [ ] **Step 1: Write the guard test first.** `test_backend_ruff_config_only_extends_the_root`: parse the backend `pyproject.toml` with `tomllib` and assert that `tool.ruff` has `extend == "../../../ruff.toml"`. Under `tool.ruff.lint`, assert there is no key in `{"ignore", "extend-ignore", "per-file-ignores", "extend-per-file-ignores", "select", "extend-select"}`, and that `known-first-party` contains `context`. Run it and confirm it fails because of `extend-per-file-ignores`.
- [ ] **Step 2: Remove the `"tests/**"` key** and fix the test violations.
  - Docstrings describe the behavior each test checks.
  - Package and module docstrings say what the test package or module covers.
  - Fixtures and helpers get one line on what they provide.
  - Split this into two commits if it helps the review: `tests/context/**`, then the rest.
- [ ] **Step 3: Delete the empty table.** The guard test now passes.
- [ ] **Step 4: Verify.**
  - The four commands pass with an unchanged test count, plus 1 for the guard test.
  - `uv run --directory <repo> ruff check --config ruff.toml --no-fix src/data-platform/backend` from the repo root reports `All checks passed!`.
- [ ] **Step 5: Commit** as `docs(backend): document tests to satisfy the root ruff rules`, and then `test(backend): guard that the backend ruff config only extends the root` (or combine them).

### Task 4: Move the console to `src/data-platform/frontend`

**Files:**
- Move: `src/console/` → `src/data-platform/frontend/` (`git mv`). The ignored `node_modules/` and `dist/` move with the directory.
- Modify: every hit of `git grep -n 'src/console' -- ':!docs/superpowers'` (today: `.gitignore`, `CLAUDE.md`, `docs/agents/project-history.md`, `platform/25-lakehouse-control-plane/README.md`, `platform/25-lakehouse-control-plane/build.sh`, `src/console/CLAUDE.md`, `src/console/README.md`). Also any CI or pre-commit `files:` pattern that names the console.

**Interfaces:** Produces the frontend at `src/data-platform/frontend`. `build.sh` builds the `console` image from it.

- [ ] **Step 1:** Record the baseline: `npm test` / `npm run build` / `npm run lint`, or whichever scripts `package.json` defines, run with `npm --prefix src/console run <script>`.
- [ ] **Step 2: Move and rewrite the path references.**
  - Run `git mv src/console src/data-platform/frontend` and rewrite each path reference.
  - In prose, call the directory "frontend" only where it means the code location. The product, image and pod stay "console".
  - Root `CLAUDE.md` "Where the rest lives" points at `src/data-platform/frontend/CLAUDE.md`.
  - Add one line to the project history.
- [ ] **Step 3: Verify.**
  - The same npm scripts give the same results from the new path.
  - `git grep -n 'src/console' -- ':!docs/superpowers'` is empty.
  - `bash -n platform/25-lakehouse-control-plane/build.sh`.
  - `test ! -e src/console`.
- [ ] **Step 4: Commit** as `refactor: move src/console to src/data-platform/frontend`.

### Task 5: Rebuild, verify on the cluster, stop

**Files:** none.

- [ ] **Step 1:** `task pre-pr KUBE_CONTEXT=retail-lakehouse` passes from the repo root.
- [ ] **Step 2:** In order, run `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh`, then `validate.sh`, then `e2e.sh`. All three must exit 0. The one known flake is the reclaimed check (`N < 20`); if it fails, rerun it once. Capture the real e2e output tail in the report, including the procedure results.
- [ ] **Step 3:** Run `kubectl get pods --namespace lakehouse-control-plane --context retail-lakehouse`. Expect:
  - api / worker / event-consumer on the new backend tag;
  - console on the new console tag, built from `src/data-platform/frontend`;
  - 0 restarts.
- [ ] **Step 4:** Stop. Do not push. The controller tells the owner.
