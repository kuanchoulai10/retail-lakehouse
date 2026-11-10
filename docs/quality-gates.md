# Quality Gates: From Commit to Canary

A change to retail-lakehouse passes six quality gates on its way from a developer's laptop to production traffic, and a seventh gate runs every night alongside them. Each gate asks one question and runs only the checks that can answer it. **A gate costs more to run than the gate before it, so cheap checks fail fast and expensive ones run only on changes that already passed everything cheaper.**

**The Taskfile says *how* to test, and CI decides *when*.** A gate is a list of test tasks, and each test task also runs on its own.

## How the Tasks Are Organised

**Gates, scopes, gate tests and components each live in their own file, so no file grows past a screen or two and adding one never means editing the others.**

| Layer | Where | Run as | What it holds |
|---|---|---|---|
| Gate | `tasks/gates/gates.yml` | `task gates:pre-pr scope=backend` | Which tests run at this point, in what order, plus `deployment-test`, the one gate test two gates share |
| Scope | `tasks/gates/frontend/frontend.yml`, `tasks/gates/backend/backend.yml` | `task gates:backend:pre-pr` | Which components belong to this side, and what each gate runs for them |
| Component | the component's own `Taskfile.yml` | `task -d src/data-platform/backend unit-test` | How this component runs each kind of test, in its own directory |
| Gate test | `tasks/gates/<gate>/<gate>.yml` | `task gates:nightly:e2e-full-test KUBE_CONTEXT=…` | Tests that span components or need a running platform, beside the one gate that runs them |

**A scope file includes the components that belong to it**: `frontend.yml` includes `design-system` and `console` (`src/data-platform/frontend`), `backend.yml` includes `backend` and `spark` (`src/data-platform/runtime/spark`), and `gates.yml` itself includes `scripts`, which belongs to neither side. **Every component uses the same task names**, `unit-test`, `component-test`, `arch-test`, `security-test`, `coverage-test`, `integration-test` and `build-test`, and defines only the ones it has. A scope calls them as `<component>:<kind>-test`, so a component that names its tests differently is invisible to the gates. The component includes are internal, which keeps them out of `task --list`; to run one alone, point `task` at its directory, for example `task -d src/design-system component-test`.

Running `task gates:pre-pr` fans out like this. Pre-commit runs first, because a formatting failure makes the rest pointless. The script tests follow. `gates:frontend:pre-pr` and `gates:backend:pre-pr` then run at the same time, each starting its components' unit tests in parallel before its slower checks. `gates:pre-pr:contract-test` runs last, once both halves pass. A failure on either side fails the gate.

Two rules keep the layers apart. **A component never calls another component**; anything that needs two of them is a gate test. **A test that needs a cluster is a gate test of a later gate**, because pre-PR runs with no services.

To add a component, give it a `Taskfile.yml` with the task names it supports, include it as internal in its scope file with `dir` set to its directory, and add one line per test kind to that scope's gate tasks. To add a kind of test, add the task to each component that has it and a line to the scope task that runs it. To add a gate test, add it to that gate's own file and call it from the gate in `gates.yml`; a test two gates run with the same checks stays one task in `gates.yml` (as `deployment-test` does, pointed at a different `KUBE_CONTEXT` by each gate), while a test whose checks differ by gate becomes two names, as `e2e-critical-test` and `e2e-full-test`, or `performance-critical-test` and `performance-full-test`, do. Task resolves a leading `:` one level up, not at the root, which is why a scope or gate file includes what it calls (`pre-pr.yml` includes `dev`, `post-merge.yml` includes `apps`) instead of reaching for the root.

## The Journey

```mermaid
timeline
    title Quality gates, one task per gate
    Before Committing <br> (task gates:pre-commit) : Merge conflict markers
                                 : Trailing whitespace
                                 : TOML syntax
                                 : Shebangs and executable bits
                                 : shellcheck
                                 : Kubernetes label standard
                                 : gitleaks secret scan
                                 : zizmor workflow audit
                                 : commitlint (commit message)
                                 : eslint and tsc (console, design system)
                                 : ty type check
                                 : ruff lint and format
    Before Opening a PR <br> (task gates:pre-pr) : + task gates:pre-commit
                                 : Script tests
                                 : Console and design-system unit tests
                                 : Story browser tests with axe
                                 : Backend and Spark unit tests
                                 : Architecture boundaries (import-linter)
                                 : Contract tests
    Before Merging <br> (task gates:pre-merge) : + task gates:pre-pr
                                 : Dependency and image security scan
                                 : Coverage floor
                                 : Integration tests
                                 : Build every image once, tagged by commit
                                 : API tests (Bruno)
                                 : Critical-path E2E test
    After Merging <br> (task gates:post-merge) : Deploy the pre-merge images
                                 : Smoke tests (validate.sh and Bruno)
    Before Releasing <br> (task gates:pre-release) : Deploy the release images
                                 : Database migration on production-sized data
                                 : Rollback and roll forward
                                 : Performance thresholds
    While Releasing <br> (task gates:release) : Canary with automatic rollback
    On a Schedule <br> (task gates:nightly) : Full E2E test
                                 : Soak test
                                 : Resilience test
                                 : Performance test
                                 : Dependency upgrade test
```

Each column lists its checks in the order they run. `+ task gates:pre-commit` and `+ task gates:pre-pr` mark where a gate runs the whole gate before it, so a gate never repeats the work of the one before it in a different order.

On a Schedule sits at the end of the line but does not follow While Releasing. It runs against staging on a timer, apart from any single change.

## The Gates

Each gate answers its question in a specific environment. **The environment grows with the gate.** Pre-PR needs no running services. Pre-merge builds a short-lived platform for one merge candidate. Post-merge and later gates run on long-lived clusters with the same images that pre-merge built.

| Gate | Command | Question it answers | Where it runs |
|---|---|---|---|
| Pre-commit | `task gates:pre-commit` | Is the code clean? | Laptop, on every `git commit` |
| Pre-PR | `task gates:pre-pr` | Is my change logically correct? | Laptop or CI, no services |
| Pre-merge | `task gates:pre-merge` | Will `main` still work after this merge? | Merge queue candidate on a short-lived platform |
| Post-merge | `task gates:post-merge KUBE_CONTEXT=…` | Is `main` healthy once deployed to the shared environment? | Staging |
| Pre-release | `task gates:pre-release KUBE_CONTEXT=…` | Can this exact build go to production? | Production-like cluster with production-scale data |
| Release | `task gates:release` | Does the release hold under real traffic? | Production canary |
| Nightly | `task gates:nightly KUBE_CONTEXT=…` | Are there problems that only show over time? | Staging, on a schedule |

### Run One Side

**A change to the console should not wait for the backend's 2,000 tests, and the reverse.** The three local gates, pre-commit, pre-PR and pre-merge, take a `scope` of `frontend`, `backend` or `all`, which is the default:

```bash
task gates:pre-commit
task gates:pre-pr scope=frontend
task gates:pre-merge scope=backend
```

Each of these gates runs a shared part, then `gates:frontend:<gate>`, `gates:backend:<gate>` or both. The shared part holds the checks that belong to neither side, such as the secret scan, shellcheck and the script tests, and the checks that span both sides, such as `contract-test`, `api-test` and `e2e-critical-test`. It runs whatever the scope. A gate passes its `scope` to the gate it starts, so `task gates:pre-merge scope=frontend` runs the frontend half of pre-PR and pre-commit as well. Pre-PR and pre-merge run the two halves in parallel; pre-commit runs them one after the other, because its hooks rewrite files. Each half also runs on its own, for example `task gates:backend:pre-pr`, and `task` rejects any other `scope` value before it runs anything.

Frontend means the console (`src/data-platform/frontend`) and the design system (`src/design-system`). Backend means every Python project, including the Spark runtime. Post-merge and the later gates test the whole deployed platform and take no `scope`.

### Pre-commit

**Pre-commit keeps style arguments, type errors and leaked secrets out of code review.** `.pre-commit-config.yaml` installs two Git hooks. The `pre-commit` hook runs every check below on the staged files, and each check's `Files` pattern decides whether it fires, so a commit that only touches the console never starts ruff. The `commit-msg` hook runs `commitlint` on the message, so it runs only on a real `git commit`, never from `task gates:pre-commit`.

**Every hook carries an `alias` naming its group**, and `pre-commit run <group> --all-files` runs only that group. `task gates:pre-commit` runs the `shared` group on every file, then `frontend`, `backend` or both, as its `scope` asks. A new hook needs an alias, or no gate runs it.

| Group | Hook | Source | What it checks | Files |
|---|---|---|---|---|
| shared | `identity` | `meta` | Prints the files each hook receives, for troubleshooting | All |
| shared | `check-hooks-apply` | `meta` | Every configured hook matches at least one file | `.pre-commit-config.yaml` |
| shared | `check-merge-conflict` | `pre-commit-hooks` | No leftover merge conflict markers | All |
| shared | `trailing-whitespace` | `pre-commit-hooks` | No trailing whitespace (fixes it) | Text |
| shared | `check-toml` | `pre-commit-hooks` | TOML files parse | `*.toml` |
| shared | `check-executables-have-shebangs` | `pre-commit-hooks` | Executable files start with a shebang | Executables |
| shared | `check-shell-scripts-are-executable` | local | Shell scripts have the executable bit | Shell |
| shared | `shellcheck` | local | Shell script static analysis | Shell |
| shared | `k8s-labels` | local | Manifests follow the Kubernetes label standard (`scripts/check_k8s_labels.py`) | `platform/` |
| shared | `commitlint` | local, `commit-msg` stage | Conventional commit message | Commit message |
| shared | `gitleaks` | `gitleaks` | No committed secrets | All |
| shared | `zizmor` | `zizmor-pre-commit` | GitHub Actions workflows are valid and safe | `.github/workflows/`, `.github/actions/` |
| frontend | `eslint-console` | local | Console lint | `src/data-platform/frontend/` |
| frontend | `tsc-console` | local | Console type check, which also covers its use of the design system | Console, design system, `package-lock.json` |
| frontend | `eslint-design-system` | local | Design-system lint | `src/design-system/` |
| frontend | `tsc-design-system` | local | Design-system type check | Design system, `package-lock.json` |
| backend | `ty` | local | Type check outside the backend project | Python |
| backend | `ty-backend` | local | Type check the backend project | `src/data-platform/backend/` |
| backend | `uv-export-backend` | local | `src/data-platform/backend/requirements.txt` matches `uv.lock` | `uv.lock`, backend `pyproject.toml` |
| backend | `ruff-check` | `ruff-pre-commit` | Python lint (fixes what it can) | Python |
| backend | `ruff-format` | `ruff-pre-commit` | Python formatting | Python |

The checks finish in seconds on staged files, so they run on every commit. `tsc` checks a whole project rather than the staged files, which makes the frontend hooks the slowest of the set, but a type error caught at commit time is still cheaper than one caught in review. `ruff` and `ty` check the scripts under `scripts/` as well, so they sit in the backend group with the rest of the Python tooling.

### Pre-PR

**Pre-PR proves the change is correct before anyone else spends time on it.** It first runs pre-commit on every file, then the script tests (`scripts:unit-test`). `gates:frontend:pre-pr` runs the design-system and console unit suites in parallel (`design-system:unit-test`, `console:unit-test`), then their `component-test`, which runs every story in a browser with axe and its keyboard play function. `gates:backend:pre-pr` runs the backend and Spark unit suites in parallel (`backend:unit-test`, `spark:unit-test`), then `backend:arch-test`, which enforces the bounded-context boundaries with `lint-imports`. `system:contract-test` comes last for either side, because it checks the console's API types against the backend. Nothing here starts a container, so a red pre-PR always points at the code, never at the environment.

### Pre-merge

**Pre-merge tests the commit that will land on `main`, not the commit the author pushed.** A merge queue rebases each candidate on the latest `main` and runs the gate on the result. Two pull requests that pass separately can still break `main` together, and this gate catches that. It first runs all of pre-PR. `gates:frontend:pre-merge` then scans and measures coverage of the design system and the console and builds the console (`security-test`, `coverage-test`, `console:build-test`), and `gates:backend:pre-merge` does the same for the backend and Spark runtime, with `backend:integration-test` before the build. The two halves run in parallel. `api-test` and `e2e-critical-test` exercise the whole platform, so they run last for either side.

Pre-merge also builds the deliverables. The `build-test` tasks build `table-maintenance-backend`, `table-maintenance-spark` and the console once, tags them with the commit, and pushes them to the registry. **Every later gate deploys those same images and never rebuilds them**, so what passed pre-merge is exactly what reaches production. The API tests and the critical-path end-to-end test then run against a short-lived platform started from those images, which is torn down afterwards.

### Post-merge

Each gate's own tests live in `tasks/gates/<gate>/<gate>.yml` and run alone as `task gates:<gate>:<name>`. They carry a `summary` instead of a `desc`, which keeps them out of `task --list`; `task --list-all` shows them and `task --summary gates:<gate>:<name>` describes one.

**Post-merge catches what only a shared, long-lived environment exposes**: leftover state, real network policies, other teams' traffic. It deploys the pre-merge images to staging with `deployment-test`. Then `smoke-test` checks that the platform answers, using `task apps:validate` and a read-only Bruno collection sent through the gateway.

### Pre-release

**Pre-release checks the risks that only matter at production scale.** `migration-test` runs the database migrations against a production-sized copy of `table-maintenance-db`. `rollback-test` rolls back to the previous release and forward again. `performance-critical-test` checks maintenance run duration and catalog API latency against release thresholds, and a breach blocks the release.

### Release

**Release is a test, not a switch.** `canary-test` sends a small share of production traffic to the new version and compares its error rate and latency with the current version. If they get worse, it rolls back automatically.

### Nightly

**Nightly runs the tests too slow to run on every merge.** `e2e-full-test` runs `platform/25-lakehouse-control-plane/e2e.sh` end to end. `soak-test` keeps CDC and maintenance running for hours. `resilience-test` kills Kafka, RustFS, Polaris, Temporal or the backend database during a run. `performance-full-test` runs the longer performance suite, console bundle size included, and compares it with previous nights. `dependency-test` tries the next `uv lock --upgrade` and `npm update`. A nightly failure does not block a merge. It opens work for the next day.

## What Runs Today

Most test tasks are planned but not built yet. **A planned task prints `TODO:// …` describing what it will do and exits 0**, so every gate already runs from start to finish, and building a task out never changes the gate's shape.

| Test task | Gate | Status |
|---|---|---|
| `pre-commit`, `gates:frontend:pre-commit`, `gates:backend:pre-commit` | Pre-commit | Runs |
| `scripts:unit-test`, `design-system:unit-test`, `console:unit-test` | Pre-PR | Runs |
| `design-system:component-test`, `console:component-test` | Pre-PR | Runs |
| `backend:unit-test`, `backend:arch-test` | Pre-PR | Runs |
| `spark:unit-test` | Pre-PR | Planned |
| `gates:pre-pr:contract-test` | Pre-PR | Console API check runs; Polaris and Spark Operator contracts planned |
| `<component>:security-test`, `<component>:coverage-test`, `backend:integration-test` | Pre-merge | Planned |
| `console:build-test` | Pre-merge | Console build runs; image build planned |
| `backend:build-test`, `spark:build-test` | Pre-merge | Planned |
| `gates:pre-merge:api-test`, `gates:pre-merge:e2e-critical-test` | Pre-merge | Planned |
| `gates:deployment-test` | Post-merge, pre-release | Planned |
| `gates:post-merge:smoke-test` | Post-merge | `apps:validate` runs; Bruno planned |
| `gates:pre-release:migration-test`, `gates:pre-release:rollback-test`, `gates:pre-release:performance-critical-test` | Pre-release | Planned |
| `gates:release:canary-test` | Release | Planned |
| `gates:nightly:e2e-full-test` | Nightly | Runs |
| `gates:nightly:soak-test`, `gates:nightly:resilience-test`, `gates:nightly:performance-full-test`, `gates:nightly:dependency-test` | Nightly | Planned |

## References

- [Powertools for AWS Lambda (Python): contributing guide](https://github.com/aws-powertools/powertools-lambda-python/blob/develop/CONTRIBUTING.md), the "Code integration journey" timeline this page adapts
- [GitHub Docs: Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [Martin Fowler: The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Google SRE Workbook: Canarying Releases](https://sre.google/workbook/canarying-releases/)
- [Mermaid: Timeline diagrams](https://mermaid.js.org/syntax/timeline.html)
- [Task: Taskfile documentation](https://taskfile.dev/docs/guide)
