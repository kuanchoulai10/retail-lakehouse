# Quality Gates: From Commit to Canary

A change to retail-lakehouse passes six quality gates on its way from a developer's laptop to production traffic, and a seventh gate runs every night alongside them. Each gate asks one question and runs only the checks that can answer it. **A gate costs more to run than the gate before it, so cheap checks fail fast and expensive ones run only on changes that already passed everything cheaper.**

**The Taskfile says *how* to test, and CI decides *when*.** A gate is a list of test tasks, and each test task also runs on its own.

## How the Tasks Are Organised

**Gates, components and system tests each live in their own place, so adding one never means editing the other two.**

| Layer | Where | Run as | What it holds |
|---|---|---|---|
| Gate | `tasks/gates.yml`, flattened into the root | `task pre-pr scope=backend` | Which tests run at this point, in what order. Never a command. |
| Component | the component's own `Taskfile.yml`, included as internal | `task -d src/data-platform/backend unit-test` | How this component runs each kind of test, in its own directory |
| System | `tasks/system.yml` | `task system:e2e-full-test KUBE_CONTEXT=…` | Tests that span components or need a running platform |

The components are `scripts`, `design-system`, `console` (`src/data-platform/frontend`), `backend` and `spark` (`src/data-platform/runtime/spark`). **Every component uses the same task names**, `unit-test`, `component-test`, `arch-test`, `security-test`, `coverage-test`, `integration-test` and `build-test`, and defines only the ones it has. A gate calls them as `<component>:<kind>-test`, so a component that names its tests differently is invisible to the gates. The component includes are internal, which keeps them out of `task --list`; to run one alone, point `task` at its directory, for example `task -d src/design-system component-test`.

Running `task pre-pr` fans out like this. Pre-commit runs first, because a formatting failure makes the rest pointless. The script tests follow. `pre-pr-frontend` and `pre-pr-backend` then run at the same time, each starting its components' unit tests in parallel before its slower checks. `system:contract-test` runs last, once both halves pass. A failure on either side fails the gate.

Two rules keep the layers apart. **A component never calls another component**; anything that needs two of them belongs in `tasks/system.yml` or a gate. **A test that needs a cluster is a system test**, because pre-PR runs with no services.

To add a component, give it a `Taskfile.yml` with the task names it supports, include it in the root `Taskfile.yml` with `dir` set to its directory, and add one line per test kind to `<gate>-frontend` or `<gate>-backend`. To add a kind of test, add the task to each component that has it and a line to the gate that runs it. To add a system test, add it to `tasks/system.yml` and to its gate.

## The Journey

```mermaid
timeline
    title Quality gates, one task per gate
    Before Committing <br> (task pre-commit) : Merge conflict markers
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
    Before Opening a PR <br> (task pre-pr) : + task pre-commit
                                 : Script tests
                                 : Console and design-system unit tests
                                 : Story browser tests with axe
                                 : Backend and Spark unit tests
                                 : Architecture boundaries (import-linter)
                                 : Contract tests
    Before Merging <br> (task pre-merge) : + task pre-pr
                                 : Dependency and image security scan
                                 : Coverage floor
                                 : Integration tests
                                 : Build every image once, tagged by commit
                                 : API tests (Bruno)
                                 : Critical-path E2E test
    After Merging <br> (task post-merge) : Deploy the pre-merge images
                                 : Smoke tests (validate.sh and Bruno)
    Before Releasing <br> (task pre-release) : Deploy the release images
                                 : Database migration on production-sized data
                                 : Rollback and roll forward
                                 : Performance thresholds
    While Releasing <br> (task release) : Canary with automatic rollback
    On a Schedule <br> (task nightly) : Full E2E test
                                 : Soak test
                                 : Resilience test
                                 : Performance test
                                 : Dependency upgrade test
```

Each column lists its checks in the order they run. `+ task pre-commit` and `+ task pre-pr` mark where a gate runs the whole gate before it, so a gate never repeats the work of the one before it in a different order.

On a Schedule sits at the end of the line but does not follow While Releasing. It runs against staging on a timer, apart from any single change.

## The Gates

Each gate answers its question in a specific environment. **The environment grows with the gate.** Pre-PR needs no running services. Pre-merge builds a short-lived platform for one merge candidate. Post-merge and later gates run on long-lived clusters with the same images that pre-merge built.

| Gate | Command | Question it answers | Where it runs |
|---|---|---|---|
| Pre-commit | `task pre-commit` | Is the code clean? | Laptop, on every `git commit` |
| Pre-PR | `task pre-pr` | Is my change logically correct? | Laptop or CI, no services |
| Pre-merge | `task pre-merge` | Will `main` still work after this merge? | Merge queue candidate on a short-lived platform |
| Post-merge | `task post-merge KUBE_CONTEXT=…` | Is `main` healthy once deployed to the shared environment? | Staging |
| Pre-release | `task pre-release KUBE_CONTEXT=…` | Can this exact build go to production? | Production-like cluster with production-scale data |
| Release | `task release` | Does the release hold under real traffic? | Production canary |
| Nightly | `task nightly KUBE_CONTEXT=…` | Are there problems that only show over time? | Staging, on a schedule |

### Run One Side

**A change to the console should not wait for the backend's 2,000 tests, and the reverse.** The three local gates, pre-commit, pre-PR and pre-merge, take a `scope` of `frontend`, `backend` or `all`, which is the default:

```bash
task pre-commit
task pre-pr scope=frontend
task pre-merge scope=backend
```

Each of these gates runs a shared part, then `<gate>-frontend`, `<gate>-backend` or both. The shared part holds the checks that belong to neither side, such as the secret scan, shellcheck and the script tests, and the checks that span both sides, such as `contract-test`, `api-test` and `e2e-critical-test`. It runs whatever the scope. A gate passes its `scope` to the gate it starts, so `task pre-merge scope=frontend` runs the frontend half of pre-PR and pre-commit as well. Pre-PR and pre-merge run the two halves in parallel; pre-commit runs them one after the other, because its hooks rewrite files. Each half also runs on its own, for example `task pre-pr-backend`, and `task` rejects any other `scope` value before it runs anything.

Frontend means the console (`src/data-platform/frontend`) and the design system (`src/design-system`). Backend means every Python project, including the Spark runtime. Post-merge and the later gates test the whole deployed platform and take no `scope`.

### Pre-commit

**Pre-commit keeps style arguments, type errors and leaked secrets out of code review.** `.pre-commit-config.yaml` installs two Git hooks. The `pre-commit` hook runs every check below on the staged files, and each check's `Files` pattern decides whether it fires, so a commit that only touches the console never starts ruff. The `commit-msg` hook runs `commitlint` on the message, so it runs only on a real `git commit`, never from `task pre-commit`.

**Every hook carries an `alias` naming its group**, and `pre-commit run <group> --all-files` runs only that group. `task pre-commit` runs the `shared` group on every file, then `frontend`, `backend` or both, as its `scope` asks. A new hook needs an alias, or no gate runs it.

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

**Pre-PR proves the change is correct before anyone else spends time on it.** It first runs pre-commit on every file, then the script tests (`scripts:unit-test`). `pre-pr-frontend` runs the design-system and console unit suites in parallel (`design-system:unit-test`, `console:unit-test`), then their `component-test`, which runs every story in a browser with axe and its keyboard play function. `pre-pr-backend` runs the backend and Spark unit suites in parallel (`backend:unit-test`, `spark:unit-test`), then `backend:arch-test`, which enforces the bounded-context boundaries with `lint-imports`. `system:contract-test` comes last for either side, because it checks the console's API types against the backend. Nothing here starts a container, so a red pre-PR always points at the code, never at the environment.

### Pre-merge

**Pre-merge tests the commit that will land on `main`, not the commit the author pushed.** A merge queue rebases each candidate on the latest `main` and runs the gate on the result. Two pull requests that pass separately can still break `main` together, and this gate catches that. It first runs all of pre-PR. `pre-merge-frontend` then scans and measures coverage of the design system and the console and builds the console (`security-test`, `coverage-test`, `console:build-test`), and `pre-merge-backend` does the same for the backend and Spark runtime, with `backend:integration-test` before the build. The two halves run in parallel. `system:api-test` and `system:e2e-critical-test` exercise the whole platform, so they run last for either side.

Pre-merge also builds the deliverables. The `build-test` tasks build `table-maintenance-backend`, `table-maintenance-spark` and the console once, tags them with the commit, and pushes them to the registry. **Every later gate deploys those same images and never rebuilds them**, so what passed pre-merge is exactly what reaches production. The API tests and the critical-path end-to-end test then run against a short-lived platform started from those images, which is torn down afterwards.

### Post-merge

The tests from here on are system tests in `tasks/system.yml`, run alone as `task system:<name>`.

**Post-merge catches what only a shared, long-lived environment exposes**: leftover state, real network policies, other teams' traffic. It deploys the pre-merge images to staging with `deployment-test`. Then `smoke-test` checks that the platform answers, using `task apps:validate` and a read-only Bruno collection sent through the gateway.

### Pre-release

**Pre-release checks the risks that only matter at production scale.** `migration-test` runs the database migrations against a production-sized copy of `table-maintenance-db`. `rollback-test` rolls back to the previous release and forward again. `performance-test` measures maintenance run duration, catalog API latency and console bundle size against thresholds.

### Release

**Release is a test, not a switch.** `canary-test` sends a small share of production traffic to the new version and compares its error rate and latency with the current version. If they get worse, it rolls back automatically.

### Nightly

**Nightly runs the tests too slow to run on every merge.** `e2e-full-test` runs `platform/25-lakehouse-control-plane/e2e.sh` end to end. `soak-test` keeps CDC and maintenance running for hours. `resilience-test` kills Kafka, RustFS, Polaris, Temporal or the backend database during a run. `dependency-test` tries the next `uv lock --upgrade` and `npm update`. A nightly failure does not block a merge. It opens work for the next day.

## What Runs Today

Most test tasks are planned but not built yet. **A planned task prints `TODO:// …` describing what it will do and exits 0**, so every gate already runs from start to finish, and building a task out never changes the gate's shape.

| Test task | Gate | Status |
|---|---|---|
| `pre-commit`, `pre-commit-frontend`, `pre-commit-backend` | Pre-commit | Runs |
| `scripts:unit-test`, `design-system:unit-test`, `console:unit-test` | Pre-PR | Runs |
| `design-system:component-test`, `console:component-test` | Pre-PR | Runs |
| `backend:unit-test`, `backend:arch-test` | Pre-PR | Runs |
| `spark:unit-test` | Pre-PR | Planned |
| `system:contract-test` | Pre-PR | Console API check runs; Polaris and Spark Operator contracts planned |
| `<component>:security-test`, `<component>:coverage-test`, `backend:integration-test` | Pre-merge | Planned |
| `console:build-test` | Pre-merge | Console build runs; image build planned |
| `backend:build-test`, `spark:build-test` | Pre-merge | Planned |
| `system:api-test`, `system:e2e-critical-test` | Pre-merge | Planned |
| `system:deployment-test` | Post-merge, pre-release | Planned |
| `system:smoke-test` | Post-merge | `apps:validate` runs; Bruno planned |
| `system:migration-test`, `system:rollback-test`, `system:performance-test` | Pre-release | Planned |
| `system:canary-test` | Release | Planned |
| `system:e2e-full-test` | Nightly | Runs |
| `system:soak-test`, `system:resilience-test`, `system:dependency-test` | Nightly | Planned |

## References

- [Powertools for AWS Lambda (Python): contributing guide](https://github.com/aws-powertools/powertools-lambda-python/blob/develop/CONTRIBUTING.md), the "Code integration journey" timeline this page adapts
- [GitHub Docs: Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue)
- [Martin Fowler: The Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html)
- [Google SRE Workbook: Canarying Releases](https://sre.google/workbook/canarying-releases/)
- [Mermaid: Timeline diagrams](https://mermaid.js.org/syntax/timeline.html)
- [Task: Taskfile documentation](https://taskfile.dev/docs/guide)
