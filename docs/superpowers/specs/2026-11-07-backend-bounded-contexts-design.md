# Backend bounded contexts

Date: 2026-11-07

## Intent

The owner wants the Apache Polaris console's whole feature set inside the project's own console. That covers browsing catalogs, namespaces, tables and views, and also managing principals, principal roles, catalog roles and grants. The console calls the project's own API, never Polaris directly, so one Keycloak login covers everything. Polaris credentials also stay in the backend, and the API is where authorization will later be enforced.

Adding these features to today's backend would put three different models on one aggregate axis:

- table maintenance: our database is the source of truth;
- catalog objects: Polaris is the source of truth;
- access control: Polaris is the source of truth.

That would blur the boundaries the architecture tests exist to protect. The owner is worried about the code being broken by a large change. So this project makes no feature change. It prepares the ground and records the rules first:

1. Rename `src/table-maintenance` to `src/data-platform`.
2. Put a bounded-context level above the aggregate axis in the backend. Move all existing code into the `table_maintenance` context.
3. Make the architecture tests work per context. Derive the aggregate list from the domain model instead of a hand-kept list.
4. Record the rules for outbound ports (Repository / Store / Gateway), external systems of record and one-time secrets in ADRs and the naming spec. Add the gateway verb `Create`.

The catalog and access contexts and the console pages come in a later project. That project can then add aggregates without restructuring.

## Goals

- `src/data-platform/` replaces `src/table-maintenance/`, with `backend/` and `runtime/spark/` under it. Every reference in tooling and docs follows the move:
  - root `pyproject.toml` workspace members and `uv.lock`
  - `.pre-commit-config.yaml`
  - `tasks/checks.yml`
  - `platform/25-lakehouse-control-plane/build.sh`
  - `.claude/skills/minikube-deploy/SKILL.md`
  - `CLAUDE.md` files, READMEs and `docs/`, except the historical `docs/superpowers/` specs and plans
- The backend has this layout:

  ```
  backend/
  ├── base/                    # shared kernel, unchanged
  ├── bootstrap/               # composition roots, unchanged in role; wires every context
  ├── context/
  │   └── table_maintenance/
  │       ├── application/     # domain/{model,service}, port/{inbound,outbound}, service, exceptions
  │       └── adapter/         # inbound, outbound, hybrid
  ├── entrypoint.py
  └── tests/
      ├── architecture/        # rules written once, run for every context
      └── context/table_maintenance/…   # today's tests, mirrored
  ```

  Inside a context everything stays as it is today: the aggregate axis, the `application` ring order, `adapter/{inbound,outbound,hybrid}`, and Temporal as a hybrid adapter.
- Contexts are independent. Context A may use context B only from its own outbound adapters, through B's inbound ports (see "Settled after the builder check"), never through B's domain, services, outbound ports or adapters. `bootstrap` may import every context. `base` imports no context.
- Every existing architecture rule holds for each context, enforced as today by import-linter contracts and `tests/architecture/`. The import-linter contracts still have no `ignore_imports`. Context independence is a new contract or test that stays green with one context and fails when a second context reaches into another's internals.
- `tests/architecture/aggregates.py` no longer holds a hand-written set. A context's aggregates are the directories under its `application/domain/model/` (except `shared`) whose package defines a subclass of `base.AggregateRoot`. Every other aggregate-axis layer of that context may hold only those names plus `shared`.
- `AGGREGATE_SQL_PACKAGES` stays a hand-written list (owner's decision), with paths updated. The existing drift test keeps guarding it.
- Behavior is unchanged:
  - all tests, `ty check`, `ruff check .` and `lint-imports` pass;
  - the rebuilt `table-maintenance-backend` image deploys through wave 25;
  - `platform/25-lakehouse-control-plane/validate.sh` and `e2e.sh` pass.
- Documentation:
  - **ADR 0005, bounded contexts and context map.** The three contexts, what each owns, which system is the source of truth, and how they relate. The maintenance `Table` and the catalog table are different models of the same thing, linked by the Iceberg table UUID (ADR 0001). Maintenance conforms to the catalog (ADR 0003).
  - **ADR 0006, choosing an outbound port.** Repository, Store and Gateway are chosen by whether the thing is one of our aggregates, not by where its data lives. An aggregate whose system of record is external (for example a Polaris principal) still gets a `{Aggregate}Repo`, with an adapter named after the technology (`PrincipalsPolarisRepo`). A Store holds data we keep that is not an aggregate. A Gateway asks an external system to do or tell something that is not loading or saving one of our aggregates.
  - **ADR 0007, one-time secrets.** An operation whose external system returns a secret once (create a principal, rotate or reset its credentials) is a Gateway, not a Repository method:
    - Ports: `CreatePrincipalGateway`, and `UpdatePrincipalCredentialsGateway` for rotate and reset.
    - The secret is never part of aggregate state and is never persisted or logged. It travels in the use case output as a value object whose `repr` hides the value (`IssuedPrincipalCredentials`).
    - The web response carries `Cache-Control: no-store`. The UI shows the secret once; rotate is the recovery path.
    - Evidence: AWS `CreateAccessKey`, GCP service account keys, Stripe keys and Polaris's own `createPrincipal` / `rotateCredentials` all issue a secret as its own operation and never return it from a later read.
  - The naming spec (`docs/superpowers/specs/2026-04-27-outbound-port-adapter-naming-convention.md`) gains `Create` in the gateway verb vocabulary and points to ADR 0006 and 0007. Wherever a test checks the verb vocabulary, the test follows.
  - `src/data-platform/backend/CLAUDE.md` describes the context level, the derived aggregate list, the independence rule, and links the three ADRs. The root `CLAUDE.md` index and `docs/agents/project-history.md` follow the move.

## Non-goals

- No catalog or access context code: no Principal, Catalog or other new aggregate, no new endpoint, no console page. Those belong to the next project.
- No runtime-visible renames: image names (`table-maintenance-backend`, `table-maintenance-spark`, `console`), the Helm chart and release `table-maintenance`, namespaces, the `GLAC_` settings prefix, database and table names, API routes, and Temporal workflow names and IDs all stay.
- No change to `base/` types or to the rules inside a context.

## Anti-goals

- A behavior change hidden inside the move. Commits that move files contain no logic edits, so a reviewer can trust `git log --follow` and the diff.
- Weakening an architecture rule to get green, for example adding `ignore_imports`, loosening a test, or skipping the context for a layer.
- A derived aggregate list that is circular. If every directory that exists is an aggregate, the test checks nothing. The list must come from the domain model's `AggregateRoot` classes, so a stray or misspelt directory in another layer still fails.
- Running Temporal workflows breaking. Workflow and activity names come from the contracts' string values, not module paths. That stays true, and the determinism and sandbox tests keep passing.

## Constraints

- Project rules apply: TDD, commits on `main`, conventional commits, every commit passing `pytest -v`, `ty check`, `ruff check .` and `lint-imports` (`task pre-pr`), no `cd`, `uv run`.
- Boundary-only imports stay: other packages import only from a boundary's `__init__`, and boundaries do not nest. The context package itself is not a boundary. Boundaries keep being derived from the directory rules (`tests/architecture/boundaries.py`).
- `src/table-maintenance/temp/` is untracked owner material. It moves with a plain `mv` into `src/data-platform/temp/` and stays uncommitted (my call).

## Decided by the owner

- Three contexts: `table_maintenance`, `catalog`, `access`. The directory shape is as above.
- `src/data-platform` is the new name.
- The aggregate list is derived automatically; `AGGREGATE_SQL_PACKAGES` stays manual.
- `Create` joins the gateway verbs. Principal creation is `CreatePrincipalGateway`; rotate and reset are `UpdatePrincipalCredentialsGateway`.
- The rules are recorded as ADRs plus the naming spec, with CLAUDE.md pointing to them.

## Settled after the builder check (my calls)

- **Move commits and green builds.** The move cannot be both a pure `git mv` and green, because every module uses absolute imports (`from application.… import …`). So:
  - Every commit stays green, and no deliberately red commit is allowed.
  - The move commit is produced by a script that does two things: it moves the files, and it rewrites module paths in import statements and in path strings (`.importlinter`, `boundaries.py`, test path constants, tooling). It changes nothing else.
  - The script is committed, or quoted in the commit message, so the commit can be reproduced.
  - Before committing, check the diff: once module paths are normalized, no line may differ. Any other edit belongs in a separate commit.
  - Losing rename tracking on files that are mostly imports (re-export `__init__.py` files) is accepted. The normalized-diff check is what proves the move changed no logic.
- **How one context uses another.** Only through the consuming context's outbound adapters, in the anti-corruption-layer style:
  - Context A defines its own outbound port in its own language.
  - An adapter of A implements that port by calling B's inbound port (use case) and mapping B's output into A's types.
  - A's `application` never imports B.
  - The independence rule: a context's `application` imports no other context; a context's adapters may import another context only through that context's `application.port.inbound`.
- **No code shared between contexts beyond `base`.** There is no `context/shared`. Each context keeps its own types, for example its own table-UUID value object. Contexts link by identifier values, not by shared classes, as ADR 0005 states.
- **Ownership of catalog roles and grants.** `access` owns principals, principal roles and catalog roles, and grants live inside the catalog-role aggregate. `catalog` owns catalogs, namespaces, tables and views. `access` does not depend on `catalog`: a grant names its target by catalog / namespace / table name, and Polaris rejects a target that does not exist. If `access` later needs to check targets itself, it does so through its own outbound port, following the rule above.

## Left to the builder

- **How the move is split into commits.** Each commit stays green, and the pure move is separate from rule changes.
- **How import-linter contracts are written per context:** one contract set per context, or contracts over `context.*` wildcards if import-linter supports them for every contract type.
- **How context independence is enforced:** a forbidden contract per context pair, or an architecture test that scans imports.
- **Whether the uv workspace package is renamed** from `table-maintenance-backend` to `data-platform-backend`. It is a tooling-only name. If renamed, the pre-commit `uv export` hook follows.
- **How a fixture context proves the per-context tests generalize** (for example a throwaway package under `tests/`) without adding a real second context.

## Verification

1. `task pre-pr` passes. `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest -v`, `ty check`, `ruff check .` and `lint-imports` each pass.
2. The derived aggregate list equals today's five names. Adding a directory without an `AggregateRoot` under any aggregate-axis layer fails the test.
3. A deliberate import from one context into another context's domain fails (shown in a test with a fixture context or a temporary file, not committed).
4. `git grep 'src/table-maintenance'` returns hits only under `docs/superpowers/` (historical).
5. `platform/25-lakehouse-control-plane/build.sh` builds the images from the new paths. A wave-25 `bootstrap.sh` + `validate.sh` and `e2e.sh` pass on the running cluster with `KUBE_CONTEXT=retail-lakehouse`.
6. ADR 0005–0007 exist, and the naming spec and both CLAUDE.md files link them.
