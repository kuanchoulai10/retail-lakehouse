# Backend Bounded Contexts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the backend under `src/data-platform/backend/context/table_maintenance/`, make every architecture rule run per context with a derived aggregate list and a context-independence rule, and record the port and secret rules as ADRs. Nothing changes at runtime.

**Architecture:** Four steps, each one green:
1. A plain directory rename (`src/table-maintenance` → `src/data-platform`).
2. A script-generated move of `application/` and `adapter/` into `context/table_maintenance/`, checked by a normalized diff.
3. A rule commit that rewrites the architecture tests and the import-linter contracts over `context.*`.
4. Docs.

The ADRs come first, because they hold no code.

**Tech Stack:** Python 3.14, uv workspace, pytest, import-linter 2.11 (wildcards `*` work in forbidden, independence and layers `containers`), ty, ruff, Helm wave 25 on minikube.

**Spec:** `docs/superpowers/specs/2026-11-07-backend-bounded-contexts-design.md`

## Global Constraints

- Commits go on `main`; no branch, no worktree, no push. Stage by explicit path. Never stage `docs/architecture.excalidraw.svg` or anything under `src/*/temp/`.
- Conventional commits: lowercase subject, every line ≤ 100 chars, message ends with a blank line and `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.
- Every commit passes these four commands, all run from the backend directory:
  - `uv run --project <backend> --directory <backend> pytest -v`
  - `… ty check`
  - `… ruff check .`
  - `… lint-imports`

  `<backend>` is `src/table-maintenance/backend` before Task 2 and `src/data-platform/backend` from Task 2 on. Pre-commit hooks run on commit; never use `--no-verify`.
- No `cd`. Use `uv run`, never bare `python` or `pytest`. `rm -rf` is hook-blocked; use `rm` on files and `rmdir` on empty directories, and `find … -name __pycache__ -type d -prune -exec rm -r {} +` for bytecode caches.
- Runtime-visible names stay as they are:
  - images `table-maintenance-backend`, `table-maintenance-spark`, `console`;
  - Helm chart and release `table-maintenance`, and namespaces;
  - the `GLAC_` prefix, DB and table names, API routes;
  - Temporal workflow names and IDs, and signal and activity string values.
- `base/` is not edited.
- No `ignore_imports` in `.importlinter`, and no loosened or skipped architecture test.
- Historical `docs/superpowers/` specs and plans keep their old paths. The one exception is the naming spec edit in Task 1.
- Temporary files go in `/Users/kcl/.claude/jobs/ffac9ee8/tmp`.

## Fixed names

| Thing | Value |
|---|---|
| New source root | `src/data-platform/` (`backend/`, `runtime/spark/`, untracked `temp/`) |
| Context package | `context/table_maintenance/` holding `application/` and `adapter/` |
| Context dotted prefix | `context.table_maintenance.` |
| Test mirror | `tests/context/table_maintenance/{application,adapter,fakes}/`. `tests/{architecture,base,bootstrap}` stay |
| Structural packages | `context/__init__.py`, `context/table_maintenance/__init__.py`, `tests/context/__init__.py`, `tests/context/table_maintenance/__init__.py`: one-line docstring, no exports, not boundaries |
| uv package names | unchanged: `table-maintenance-backend` (matches the image) and `table-maintenance-spark` (ruling: the rename is optional, and keeping them avoids churn in `requirements.txt` and the lock file) |
| Move script | `scripts/move_backend_into_context.py` (committed with the move) |
| Context helpers | `tests/architecture/contexts.py`: `CONTEXT_ROOT: Path`, `context_names() -> list[str]`, `context_dir(name: str) -> Path`, `context_module(name: str) -> str` |
| Aggregate derivation | `tests/architecture/aggregates.py`: `derive_aggregates(model_package: str) -> set[str]`, `aggregates(context: str) -> set[str]` |
| Independence checker | `tests/architecture/test_context_independence.py`: `cross_context_violations(backend: Path) -> list[str]` |
| ADRs | `docs/adr/0005-bounded-contexts-and-context-map.md`, `0006-choosing-an-outbound-port.md`, `0007-one-time-secrets.md` |

## Review Focus

- **Dotted module paths in plain strings.** `AGGREGATE_SQL_PACKAGES`, `importlib.import_module`, `pkgutil` prefixes and `SHARED_SQL` must be rewritten too. If one is missed, the `migrate` component fails only at runtime. Task 3 adds an import smoke step that imports all four entry modules and runs `create_schema` against SQLite.
- **Old directories left behind.** An `application/__pycache__/` left after the move turns `application` into a namespace package that still imports. Task 3 deletes the caches and asserts that the old top-level directories are gone.
- **Temporal wire names.** Workflow, signal and activity names must not depend on module paths. Task 3 runs `test_wire_names.py`, the determinism test and the sandbox test after the move, and greps `@workflow.defn` / `@activity.defn` for any name argument that is missing.
- **Fixture contexts in `sys.modules`.** Fixture packages built under `tmp_path` must get a unique top-level name for each test. Otherwise a cached module from one test leaks into the next. Task 4's fixture helper uses `f"fixture_ctx_{uuid4().hex}"`.
- **A rule that silently covers one context.** A contract or test that hard-codes `table_maintenance` would pass now and never check a second context. Task 4 adds guards: no import-linter expression names a concrete context, and no architecture test except `test_aggregates.py` names `table_maintenance`.

---

### Task 1: ADRs 0005–0007 and the `Create` gateway verb

**Files:**
- Create: `docs/adr/0005-bounded-contexts-and-context-map.md`, `docs/adr/0006-choosing-an-outbound-port.md`, `docs/adr/0007-one-time-secrets.md`
- Modify: `docs/superpowers/specs/2026-04-27-outbound-port-adapter-naming-convention.md` (the "Gateway Verb Vocabulary" table near line 37, plus a "See also" line)

**Interfaces:** Produces the three ADR paths, which Task 5 links from both CLAUDE.md files.

- [ ] **Step 1: Write the three ADRs.** Use the format of `docs/adr/0003-events-as-hints-catalog-as-truth.md`: H1 `# N. Title`, `Date: 2026-11-07`, `Status: Accepted`, then `## Context`, `## Considered options`, `## Decision` and `## Consequences`. The content comes from the spec's Goals → Documentation bullets and its "Settled after the builder check" section:
  - **0005:** the three contexts with their owned aggregates and source of truth, the anti-corruption rule, and no shared code beyond `base`. The maintenance `Table` and the catalog table are linked by Iceberg UUID (cite ADR 0001), and maintenance conforms to the catalog (cite ADR 0003). `access` owns the catalog roles and grants, and does not depend on `catalog`.
  - **0006:** the port is chosen by whether the thing is our aggregate, not by where its data lives. Example: `PrincipalsRepo` / `PrincipalsPolarisRepo`. A Store holds non-aggregate data we keep. A Gateway asks an external system to do or tell something.
  - **0007:** `CreatePrincipalGateway` and `UpdatePrincipalCredentialsGateway`. `IssuedPrincipalCredentials` has a redacting `repr` and is never persisted or logged. The web response carries `Cache-Control: no-store`. The UI shows the secret once, and rotate is the recovery path. Evidence: AWS `CreateAccessKey`, GCP service-account keys, Stripe keys, Polaris `createPrincipal` / `rotateCredentials`.

  Each ADR states that no code implements it yet; the catalog and access contexts come in a later project.
- [ ] **Step 2: Edit the naming spec.** Add a `Create` row to the verb table. Semantics: "Ask an external system to create something that returns data only once (for example a credential); see ADR 0007". Add a line under the table pointing to ADR 0006 and 0007 (relative links `../../adr/…`). No test checks the gateway verb vocabulary today (`KNOWN_VERBS` in `test_service_structure.py` is the service list and already has `Create`), so no test changes.
- [ ] **Step 3: Verify.** `ls docs/adr` lists 0001–0007. Every relative link in the new files resolves: check each `](…)` target with `test -f`.
- [ ] **Step 4: Commit** `docs(adr): record bounded contexts, outbound port choice and one-time secrets`.

### Task 2: Rename `src/table-maintenance` to `src/data-platform`

**Files:**
- Move: `src/table-maintenance/` → `src/data-platform/` (`git mv`; the untracked `temp/` moves with the directory)
- Modify: every file that `git grep -l 'src/table-maintenance' -- ':!docs/superpowers'` lists today:
  - `.claude/skills/minikube-deploy/SKILL.md`
  - `.pre-commit-config.yaml` (lines 56, 59, 62, 68, 70)
  - `CLAUDE.md`
  - `DEVELOPER_AGENT_PROMPT.md`, `REVIEWER_AGENT_PROMPT.md`
  - `docs/iceberg/table-maintenance.md`
  - `platform/25-lakehouse-control-plane/build.sh` (`BACKEND_DIR`, `SPARK_DIR`)
  - `pyproject.toml` (workspace members)
  - `src/data-platform/runtime/spark/README.md`
  - `tasks/checks.yml` (lines 29, 35, 47)
  - `uv.lock`
- Also check the nested `CLAUDE.md` files and `docs/agents/*.md` for the bare form `table-maintenance/backend` and update it.

**Interfaces:** Produces the backend at `src/data-platform/backend`. Every later task uses this path.

- [ ] **Step 1: Write the failing check.** Run `git grep -n 'src/table-maintenance' -- ':!docs/superpowers'`. It prints hits now; afterwards it must print nothing.
- [ ] **Step 2: Move.** Run `git mv src/table-maintenance src/data-platform`. Then check:
  - `test -d src/data-platform/temp`;
  - `git status --short src/data-platform/temp` shows `??`, so the directory is still untracked;
  - `test ! -e src/table-maintenance`.
- [ ] **Step 3: Rewrite references.** Replace `src/table-maintenance/` with `src/data-platform/` in the files listed above. Make the matching prose edits ("table-maintenance backend" in a path context). Then run `uv lock`; `git diff uv.lock` may change only the workspace member paths. Leave the uv package names, image names and `tasks/checks.yml` task descriptions unchanged.
- [ ] **Step 4: Verify.**
  - The Step 1 grep prints nothing.
  - The four project commands pass from `src/data-platform/backend`.
  - `uv run --project src/data-platform/runtime/spark --directory src/data-platform/runtime/spark pytest -q` gives the same result as at the old path before the move (run it there first).
  - `bash -n platform/25-lakehouse-control-plane/build.sh` passes.
- [ ] **Step 5: Commit** `refactor: rename src/table-maintenance to src/data-platform`. Stage the renamed tracked tree with `git add src/data-platform src/table-maintenance` together with the listed files; check with `git status` that nothing under `temp/` is staged.

### Task 3: Script-generated move into `context/table_maintenance`

**Files:**
- Create: `scripts/move_backend_into_context.py`
- Create: the four structural `__init__.py` files from Fixed names
- Move: `backend/application/`, `backend/adapter/` → `backend/context/table_maintenance/`; `backend/tests/{application,adapter,fakes}/` → `backend/tests/context/table_maintenance/`
- Modify (only through the script, except the residual list below): every `.py` file under `src/data-platform/backend`, plus `.importlinter`

**Interfaces:**
- Consumes: the backend at `src/data-platform/backend` (Task 2).
- Produces the post-move dotted paths:
  - `context.table_maintenance.application.…` and `context.table_maintenance.adapter.…`;
  - `tests.context.table_maintenance.{application,adapter,fakes}.…`.

  `tests/architecture/*` still checks only this one context, at its new path. Task 4 generalizes it.

The script takes `move` and `check <BASE>`.

- **`move`:**
  1. `git mv` the directories listed above and write the four `__init__.py` files.
  2. Rewrite dotted references. A token `application.` or `adapter.` not preceded by `[\w.]` becomes `context.table_maintenance.application.` or `context.table_maintenance.adapter.`. `tests.application.`, `tests.adapter.` and `tests.fakes.` become `tests.context.table_maintenance.…`. This covers imports, `import x.y` attribute chains such as `application.service.__path__`, and dotted strings.
  3. Rewrite path forms. A string literal starting with `application/` or `adapter/` gets `context/table_maintenance/` in front. A `/ "application"` or `/ "adapter"` path segment straight after `BACKEND` (or the file's own backend-root name) gets `/ "context" / "table_maintenance"` in front.
  4. Rewrite the `.importlinter` module names the same way.
- **`check <BASE>`:**
  1. For every file in the move, read the new text and apply the inverse substitutions.
  2. Compare the result line by line with `git show <BASE>:<old path>`.
  3. Print each differing line as `residual: <new path>:<line>: <text>`.
  4. Exit 0 only when every residual line is in the script's `ALLOWED_RESIDUALS`.

  `ALLOWED_RESIDUALS` holds the lists of top-level package names. These cannot be expressed as a prefix substitution:
  - `.importlinter` `root_packages` (`adapter`, `application` → `context`);
  - `PROJECT_PACKAGES` in `tests/architecture/boundaries.py`;
  - `SOURCE_PACKAGES` in `test_inheritance_depth.py`;
  - `EXPECTED_TOP_LEVEL` in `test_directory_structure.py`.

  Each of these becomes the same tuple or set with `"context"` in place of `"application"` and `"adapter"`. Every other line must normalize to its old text. (Ruling: a list of top-level package names is a module path list, and the checker shows it explicitly. Cost if wrong: the reviewer reads four extra lines.)

- [ ] **Step 1: Record BASE** (`git rev-parse HEAD`) and confirm the suite is green there.
- [ ] **Step 2: Write the script.** Write `scripts/move_backend_into_context.py` with the `move` and `check` subcommands described above. It is stdlib only and passes ruff. The script is a one-off tool, so it gets no unit tests (ruling): its proof is `check`.
- [ ] **Step 3: Run `move`,** then make the four residual edits by hand.
- [ ] **Step 4: Clean leftovers.** Run `find src/data-platform/backend -name __pycache__ -type d -prune -exec rm -r {} +`. Then check `test ! -e src/data-platform/backend/application && test ! -e src/data-platform/backend/adapter && test ! -e src/data-platform/backend/tests/application && test ! -e src/data-platform/backend/tests/adapter && test ! -e src/data-platform/backend/tests/fakes`.
- [ ] **Step 5: Run `check <BASE>`.** Expected: exit 0, and only the four allowed residual groups are printed.
- [ ] **Step 6: Verify behavior.**
  - The four project commands pass.
  - The same number of tests is collected as at BASE (`pytest --collect-only -q | tail -1`, before and after).
  - Import smoke: `uv run --directory src/data-platform/backend python -c "import entrypoint, bootstrap.api, bootstrap.worker, bootstrap.event_consumer, bootstrap.migrate; from sqlalchemy import create_engine; from context.table_maintenance.adapter.outbound.shared.sql import create_schema; create_schema(create_engine('sqlite://'))"` exits 0. If `create_schema` is not exported there, use its boundary as listed in `boundaries()`.
  - `git grep -nE '^\s*(from|import) (application|adapter)\b' src/data-platform/backend` prints nothing.
  - `git grep -nP '@(workflow|activity)\.defn\b(?!\()' src/data-platform/backend` is reviewed: every definition has an explicit name, or takes it from a contract StrEnum. Report what it shows.
- [ ] **Step 7: Commit** `refactor(backend): move table maintenance into context/table_maintenance`. The body must contain:
  - the script invocation (`uv run scripts/move_backend_into_context.py move` + `check <BASE>`);
  - the residual list;
  - one line saying the commit holds no logic edits.

### Task 4: Per-context architecture rules, derived aggregates, context independence

**Files:**
- Create: `tests/architecture/contexts.py`, `tests/architecture/test_aggregates.py`, `tests/architecture/test_context_independence.py`, `tests/architecture/fixture_context.py` (helper: `build_fixture_context(root: Path, files: dict[str, str]) -> str`, which writes files under `root/<unique name>/…` and returns the unique top-level package name; the caller adds `root` with `monkeypatch.syspath_prepend`)
- Modify: `tests/architecture/aggregates.py`, `boundaries.py`, and every `tests/architecture/test_*.py` that holds a `context/table_maintenance` path or dotted prefix after Task 3; `.importlinter`; `tests/architecture/test_importlinter_config.py`
- All paths are under `src/data-platform/backend/`.

**Interfaces:**
- Consumes: the Task 3 layout.
- Produces:
  - `context_names() -> list[str]`: the sorted names of packages under `CONTEXT_ROOT = BACKEND / "context"`.
  - `context_dir(name) -> Path`.
  - `context_module(name) -> str`, which returns `f"context.{name}"`.
  - `derive_aggregates(model_package: str) -> set[str]`: imports `model_package` and returns the names of its child packages, except `shared`, in which some module (found with `pkgutil.walk_packages`) defines a class `c` with `c.__module__ == module.__name__`, `issubclass(c, AggregateRoot)` and `c is not AggregateRoot`.
  - `aggregates(context) -> set[str]`, which is `derive_aggregates(f"{context_module(context)}.application.domain.model")`.
  - `cross_context_violations(backend: Path) -> list[str]`: scans `backend/context/<A>/**/*.py` with `ast`, including `TYPE_CHECKING` blocks, and reports any import of `context.<B>…` with B ≠ A when the importing file is under `A/application/`, or under `A/adapter/` and the target does not start with `context.<B>.application.port.inbound`. It also reports any import of `context…` from a file under `backend/base/`. Each entry is `"<relative path>:<line> <target>"`.

- [ ] **Step 1: Write the failing tests.**
  - `test_aggregates.py`:
    - `test_table_maintenance_aggregates_are_derived`: `assert aggregates("table_maintenance") == {"table", "table_maintenance_run", "table_maintenance_preset", "table_discovery_rule", "table_discovery_settings"}`.
    - `test_package_without_aggregate_root_is_not_an_aggregate`: the fixture has `application/domain/model/widget/__init__.py`, which defines `class Widget(AggregateRoot[WidgetId])` with a matching `WidgetId(EntityId)`, plus `stray/__init__.py` holding only a dataclass and `shared/__init__.py` holding an AggregateRoot subclass. `derive_aggregates(f"{name}.application.domain.model") == {"widget"}`.
  - `test_aggregate_axis.py`:
    - Refactor it around `axis_violations(context_root: Path, aggregates: set[str]) -> list[str]`.
    - Parametrize the real check over `context_names()`.
    - Add `test_directory_without_aggregate_root_fails_the_axis`: a `tmp_path` tree with `application/service/ghost/__init__.py` and `aggregates={"widget"}` gives exactly one violation that names `ghost`.
  - `test_context_independence.py`:
    - `test_contexts_do_not_reach_into_each_other`: `cross_context_violations(BACKEND) == []`.
    - `test_cross_context_import_rules`: a `tmp_path` tree with `context/alpha` and `context/beta`, where the alpha files import:
      - `context.beta.application.domain.model.thing` from `alpha/application/service/s.py`: a violation;
      - `context.beta.application.port.inbound` from `alpha/adapter/outbound/ok.py`: allowed;
      - `context.beta.application.port.outbound` from `alpha/adapter/outbound/bad.py`: a violation;
      - `context.beta.adapter.outbound` from `alpha/adapter/inbound/web/w.py`: a violation;
      - `context.alpha.application.domain.model` from `alpha/adapter/outbound/own.py`: allowed;
      - and `base/b.py` imports `context.alpha`: a violation.

      Expect exactly the 4 violations, by path.
  - `test_importlinter_config.py`:
    - `test_root_packages_are_base_bootstrap_context`: the set equals `{"base", "bootstrap", "context"}`.
    - `test_contracts_name_no_single_context`: no value in any contract section matches `\bcontext\.(?!\*)` (every context reference is `context.*`).
    - `REQUIRED_CONTRACTS` keeps the same 14 names.
  - `test_architecture_tests_name_no_context`: a guard in `test_aggregates.py`. No `tests/architecture/*.py` other than `test_aggregates.py` contains `"table_maintenance"`, `context.table_maintenance` or `context/table_maintenance`.
- [ ] **Step 2: Run them.** `pytest tests/architecture -v` fails: the helpers do not exist yet, and the guard lists the Task 3 hard-coded paths.
- [ ] **Step 3: Implement.**
  - Write `contexts.py`, `aggregates.py` (with the hand-written set removed) and `fixture_context.py`.
  - Rewrite `boundaries.py` so the aggregate layers, `application/exceptions`, the inbound channels, the outbound aggregates and the hybrid sides are collected for each context under `context_dir(name)`. `base`, `bootstrap/configs` and `bootstrap/container` stay global.
  - In every other architecture test, replace each module-level constant that names the context with `@pytest.mark.parametrize("context", context_names())`, built from `context_dir` / `context_module`. Change no assertion inside a rule: only where it looks.
  - `test_directory_structure`: the top level is `{"base", "bootstrap", "context"}`, and each context holds exactly `{"application", "adapter"}`.
  - Rewrite the 14 contracts in `.importlinter` over `context.*`. Examples:
    - `domain-pure`: `source_modules = context.*.application.domain`.
    - `application-ring-order`: `containers = context.*.application`, with layers `service`, `port`, `domain.service`, `domain.model`.
    - `base-isolation` and `configs-leaf`: forbid `context`.
  - Keep each contract's name, type and forbidden third-party list.
- [ ] **Step 4: Run.** `pytest tests/architecture -v` passes, and so do the four project commands. `lint-imports` reports `14 kept, 0 broken`.
- [ ] **Step 5: Show the rule fails across contexts (spec Verification 3; not committed).**
  1. Create the throwaway files `context/scratch/__init__.py`, `context/scratch/application/__init__.py` and `context/scratch/application/probe.py`, where `probe.py` holds `from context.table_maintenance.application.domain.model.table import Table`.
  2. Run `pytest tests/architecture/test_context_independence.py -q`. Expect it to fail and name `probe.py`.
  3. Run `lint-imports` and report the result. It is expected to stay green, because a wildcard contract cannot express "another context"; the test is the guard.
  4. Delete the three files and `rmdir` the directories. `git status` must be clean apart from the task's changes.
  5. Paste the failing output into the report.
- [ ] **Step 6: Commit** `test(backend): run architecture rules per context with derived aggregates`.

### Task 5: Documentation follows the structure

**Files:**
- Modify: `src/data-platform/backend/CLAUDE.md`; root `CLAUDE.md` ("Project Overview", "Where the rest lives", "Project Vision"); `docs/agents/project-history.md`
- Modify (path wording only): `docs/iceberg/table-maintenance.md` and the wave-25 `README.md`, where they describe the backend layout as `application/` / `adapter/` at the root

**Interfaces:** Consumes the Fixed names and the Task 4 helper names.

- [ ] **Step 1: Backend CLAUDE.md.**
  - Update the structure tree to `base/`, `bootstrap/`, `context/<name>/{application,adapter}/`, `entrypoint.py` and `tests/{architecture,base,bootstrap,context/<name>}`.
  - Write the layering diagram and the rules with `context.<name>.` prefixes.
  - Add a "Bounded contexts" section:
    - today one context, `table_maintenance`; `catalog` and `access` are planned (ADR 0005);
    - the independence rule as the spec states it;
    - no `context/shared`.
  - Replace "Adding an aggregate means updating `tests/architecture/aggregates.py`" with: aggregates are derived from `AggregateRoot` subclasses (`tests/architecture/aggregates.py`); `AGGREGATE_SQL_PACKAGES` is still updated by hand.
  - Add "Adding a context": create `context/<name>/{application,adapter}`; the architecture tests and the `context.*` contracts pick it up.
  - Add `Create` to the gateway verb list.
  - Link ADR 0005–0007 from the outbound-port section.
- [ ] **Step 2: Root CLAUDE.md and history.**
  - Point the index row at `src/data-platform/backend/CLAUDE.md`.
  - Make the overview say `src/data-platform` and the context level.
  - Add a dated 2026-11-07 entry to `docs/agents/project-history.md`: the rename, the context move, derived aggregates, the context independence rule, ADR 0005–0007, and the `Create` verb.
- [ ] **Step 3: Verify.**
  - `git grep -n 'src/table-maintenance' -- ':!docs/superpowers'` prints nothing.
  - `git grep -nE '0005|0006|0007' -- CLAUDE.md src/data-platform/backend/CLAUDE.md` shows the links in both files.
  - Every linked path exists.
- [ ] **Step 4: Commit** `docs: describe the context level and link adr 0005-0007`.

### Task 6: Rebuild and verify on the cluster

**Files:** none. If a fix is needed, it is a separate `fix(...)` commit with its own failing check first.

- [ ] **Step 1:** Run `task pre-pr` from the repo root. It must pass.
- [ ] **Step 2:** Run `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh`. It runs `build.sh` from the new paths, loads the images and upgrades the release. Expect exit 0, with the images built from `src/data-platform/...`.
- [ ] **Step 3:** Run `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/validate.sh` and then `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh`. Both must exit 0. On a reclaimed-check failure of the form `N < 20`, rerun once: this is the known mid-write compaction follow-up. Report both runs.
- [ ] **Step 4:** Run `kubectl get pods --namespace lakehouse-control-plane --context retail-lakehouse`. Every pod must be Running or Completed, with no new restarts. Report the image tags in use.
