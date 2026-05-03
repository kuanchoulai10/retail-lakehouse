# Docs Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `docs/index.md` and `docs/prerequisites.md` back in sync with the current repo, and add a new `docs/deployment.md` that walks a reader from "tools installed" to "everything running" via `task onboard`.

**Architecture:** Three independent doc edits + one nav update in `mkdocs.yml`. `index.md` is repositioned as a portfolio landing page (three pillar tabs + architecture diagrams). `prerequisites.md` is reduced to a Homebrew install line that mirrors the `task onboard` preconditions. `deployment.md` is a new "Deployment / Configuration" template page covering the deploy-method choice, what `task onboard` does, and the `platform/` numeric layering. Manual `colima start` / `minikube start` commands move from prerequisites into deployment as the explanation of `cluster:bootstrap`.

**Tech Stack:** MkDocs (Material theme), pymdownx tabbed/admonitions, the project's `writing-docs` skill conventions, Taskfile (`task serve-docs`).

**Spec:** [`docs/superpowers/specs/2026-05-03-docs-refresh-design.md`](../specs/2026-05-03-docs-refresh-design.md)

**Conventions:** Every doc edit must follow the project's `writing-docs` skill (lead with *why*, backtick all file paths / env vars / identifiers, language hints on every code block, no ASCII art, no stacked admonitions, `## References` only when there are external links worth citing — the three pages here are introductory and may legitimately omit it; spec has no requirement). Tables are appropriate for the deploy-method comparison and platform-layering rows.

---

## Files Touched

| File | Action | Responsibility |
|------|--------|----------------|
| `docs/index.md` | Rewrite | Portfolio landing page: tagline, 3-pillar Highlights, architecture diagrams, link to prerequisites/deployment |
| `docs/prerequisites.md` | Rewrite | Hardware spec + single Homebrew install line + pointer to deployment.md |
| `docs/deployment.md` | Create | TL;DR → deploy-method comparison → `task onboard` breakdown → platform layering → validate → tear down |
| `mkdocs.yml` | Modify (nav block, lines 3–6) | Insert `deployment.md` between `prerequisites.md` and the `Argo CD` group |

No SVGs, JS/CSS, or theme settings are touched. The existing `architecture.drawio.svg`, `trino-otel.drawio.svg`, and `assets/k8s-env.excalidraw.svg` are referenced as-is.

---

## Task 1: Add `deployment.md` to mkdocs nav

Doing this first lets the new file render the moment it lands; otherwise the page is invisible to `task serve-docs` until the nav is touched.

**Files:**
- Modify: `mkdocs.yml:3-6`

- [ ] **Step 1: Insert the nav entry**

Edit `mkdocs.yml`. The current nav top reads:

```yaml
nav:
  - index.md
  - prerequisites.md
  - Argo CD:
```

Change it to:

```yaml
nav:
  - index.md
  - prerequisites.md
  - deployment.md
  - Argo CD:
```

No other lines change.

- [ ] **Step 2: Verify mkdocs config still parses**

Run: `task serve-docs` (in a separate terminal — leave it running for the rest of the plan).

Expected: server starts on `http://127.0.0.1:8000`. The nav shows a `deployment.md` entry. Clicking it shows a 404 / "page not found" (file does not exist yet) — that is correct at this point.

- [ ] **Step 3: Commit**

```bash
git add mkdocs.yml
git commit -m "docs(nav): reserve deployment.md slot between prerequisites and Argo CD"
```

---

## Task 2: Create `docs/deployment.md`

Create the new page next so the nav slot from Task 1 has content. Subsequent tasks can then link to it from `index.md` and `prerequisites.md` without dangling references.

**Files:**
- Create: `docs/deployment.md`

- [ ] **Step 1: Write the file**

Create `docs/deployment.md` with the content below. The structure follows the `writing-docs` "Deployment / Configuration" template: opener states the goal and starting state, then one H2 per area, each H2 leads with *why* before *how*.

````markdown
# Deployment

`task onboard` brings the entire stack — colima VM, minikube cluster, every app under `platform/`, and the local Python/Node toolchain — up in a single command. This page assumes the tools from [Prerequisites](prerequisites.md) are already installed and walks through the one-shot bootstrap, the deploy-method choice, the layering inside `platform/`, validation, and tear-down.

## Quick start

Pick a name for the kube context (any string; `retail-lakehouse` is the convention used throughout this repo) and run:

```bash
task onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=argocd
```

Expect 10–20 minutes on first run. When it returns, the cluster is up, every `platform/` app is healthy, and the local dev environment is wired.

## Choose a deploy method

`DEPLOY_METHOD` controls how `platform/` apps land in the cluster. Both end up at the same place; they differ in how you observe and debug the rollout.

| Method | What it does | When to pick it |
|--------|--------------|-----------------|
| `scripts` | Runs each `platform/*/bootstrap.sh` directly in dependency order | First-time exploration; failures surface step-by-step in the terminal |
| `argocd` | Bootstraps Argo CD itself, then applies the `app-of-apps` manifest under `charts/app-of-apps/` | Recommended; mirrors a real GitOps workflow and gives you a UI to inspect drift and health |

You can switch methods later by tearing down (`task offboard`) and re-running `task onboard` with the other value.

## What `task onboard` does

`task onboard` is a thin orchestration over three sub-tasks. Knowing what each one does makes failures easier to localise.

### `cluster:bootstrap` — provision the local Kubernetes cluster

The cluster runs inside a colima-managed Linux VM, with minikube on top. The Taskfile defaults are `CPU=9`, `MEMORY=28` (GiB), `DISK_SIZE=120` (GiB), and minikube is given the VM's memory minus 2 GiB so colima itself has room to breathe. Override any of them as Taskfile vars (e.g. `task onboard KUBE_CONTEXT=… MEMORY=20`).

The two underlying commands, in case you want to reproduce them by hand or understand what's running on your machine:

```bash title="equivalent of cluster:bootstrap-colima"
colima start \
  --cpu 9 \
  --memory 28 \
  --disk 120 \
  --runtime docker \
  --profile retail-lakehouse
```

```bash title="equivalent of cluster:bootstrap-minikube"
minikube start \
  --profile retail-lakehouse \
  --nodes 1 \
  --cpus 9 \
  --memory 26G \
  --disk-size 120G \
  --driver docker \
  --container-runtime docker \
  --kubernetes-version v1.33.2 \
  --addons registry --addons metrics-server \
  --insecure-registry "10.0.0.0/24" \
  --delete-on-failure
```

`--addons registry` exposes a local container registry so images built inside the project can be pushed without leaving the machine. `metrics-server` enables `kubectl top`. `--insecure-registry "10.0.0.0/24"` permits pushes to that registry over plain HTTP.

![](./assets/k8s-env.excalidraw.svg)
/// caption
K8s Cluster Environment
///

### `apps:bootstrap-by-{scripts|argocd}` — install every app under `platform/`

The selected `DEPLOY_METHOD` decides which sub-task runs. Both walk the `platform/` tree in numeric order (see [Platform layering](#platform-layering) below). The `scripts` path interleaves `bootstrap.sh` and `validate.sh` per tier so a failure stops the cascade early; the `argocd` path hands the whole tree to Argo CD via `app-of-apps` and lets sync waves enforce the same ordering.

### `dev:sync` — local toolchain

Wires the host machine up for development against the running cluster: installs Python deps with `uv`, Node deps with `npm`, and the project's `pre-commit` hooks. Safe to re-run.

## Platform layering

Directories under `platform/` are prefixed with a numeric tier. Lower numbers must be ready before higher numbers — the prefix encodes the dependency order that `bootstrap-by-scripts` walks line-by-line and that the Argo CD `app-of-apps` encodes via sync waves.

| Prefix | Tier | Examples |
|--------|------|----------|
| `00`–`02` | Argo CD itself (only used when `DEPLOY_METHOD=argocd`) | `00-argocd`, `01-argocd-health-checks`, `02-argocd-apps` |
| `10` | Cluster-wide operators and control planes | `10-cert-manager`, `10-kube-prometheus`, `10-strimzi-operator` |
| `11` | Operators that depend on tier 10 | `11-keda`, `11-spark-operator`, `11-otel-operator` |
| `20` | Stateful infra and standalone services | `20-kafka-cluster`, `20-mysql`, `20-minio`, `20-jaeger-thanos`, `20-jaeger-trino`, `20-polaris-db` |
| `21` | Apps consuming tier-20 services | `21-polaris`, `21-kafka-debezium-mysql-connector` |
| `22` | Apps consuming tier-21 outputs | `22-kafka-iceberg-connector` |
| `23` | Top-level query/UX layer | `23-trino` |
| `25` | Application backend (table maintenance) | `25-tbl-maint-db`, `25-tbl-maint-bcknd`, `25-tbl-maint-schdlr` |
| `30` | Cross-cutting layer above everything | `30-thanos` |

Tier `24-e2e-validation` exists alongside the others and runs end-to-end checks once the upstream tiers are healthy.

## Validate

Once `task onboard` returns, re-run validation any time you want a quick health check:

```bash
task apps:validate KUBE_CONTEXT=retail-lakehouse
```

It runs every `platform/*/validate.sh` in parallel. A non-zero exit means at least one app failed its readiness probe.

## Tear down

To free the resources entirely:

```bash
task offboard KUBE_CONTEXT=retail-lakehouse
```

This deletes the minikube cluster and the colima VM. Both deletes are no-ops if the targets don't exist, so it's safe to re-run.
````

- [ ] **Step 2: Verify the page renders**

In the browser tab from Task 1, refresh `http://127.0.0.1:8000/deployment/`.

Expected:
- Page title is "Deployment"
- All three code blocks render with syntax highlighting (`bash` on each)
- Both tables render
- The `k8s-env.excalidraw.svg` image renders with caption "K8s Cluster Environment"
- The `[Prerequisites](prerequisites.md)` and `[Platform layering](#platform-layering)` links work
- mkdocs server log has no warnings about broken links or missing files for this page

- [ ] **Step 3: Commit**

```bash
git add docs/deployment.md
git commit -m "docs: add top-level deployment guide"
```

---

## Task 3: Rewrite `docs/prerequisites.md`

Now that `deployment.md` exists, prerequisites can shed its cluster-setup section and link forward.

**Files:**
- Modify (full rewrite): `docs/prerequisites.md`

- [ ] **Step 1: Replace the file contents**

Overwrite `docs/prerequisites.md` with:

````markdown
# Prerequisites

This page lists the macOS host requirements and tools needed before running `task onboard`. Once they're installed, head to [Deployment](deployment.md) to bring the stack up.

## Hardware

This project is developed and tested on a Mac mini (2024) with the following specifications. They define the comfortable working envelope, not a hard floor — but the colima VM defaults (`CPU=9`, `MEMORY=28`, `DISK_SIZE=120`) assume a machine in this ballpark.

- Apple M4 chip
- 10-core CPU
- 10-core GPU
- 16-core Neural Engine
- 32 GB RAM
- 512 GB SSD

## Install required tools

Every tool below is checked by `task onboard` as a precondition; the bootstrap aborts early if anything is missing. Install them all in one go with [Homebrew](https://brew.sh/):

```bash
brew install \
  colima docker kubectl minikube helm sops git \
  python@3.13 uv jsonnet jsonnet-bundler gettext \
  openjdk@21 node
```

A few entries warrant a one-liner so the names line up with the binaries the preconditions check for:

- `gettext` provides the `envsubst` binary used for templating Kubernetes manifests.
- `openjdk@21` provides `keytool`, used to build Java truststores for Trino.
- `jsonnet-bundler` provides the `jb` binary for vendoring jsonnet libraries.
- `node` provides `npm`, used by the docs and commit-lint toolchains.

After installing, make sure `docker` is using the colima context once colima is started later (`docker context ls`).

## Next step

Tools installed? Continue to [Deployment](deployment.md).
````

- [ ] **Step 2: Verify the page renders**

Refresh `http://127.0.0.1:8000/prerequisites/` in the browser.

Expected:
- Page title is "Prerequisites"
- The hardware bullets render
- The `brew install` block renders with `bash` highlighting
- The `[Deployment](deployment.md)` links resolve (no broken-link warning in the mkdocs server log)
- No reference to `colima start`, `minikube start`, or the `k8s-env.excalidraw.svg` image remains on this page

- [ ] **Step 3: Commit**

```bash
git add docs/prerequisites.md
git commit -m "docs(prerequisites): trim to tools installation only"
```

---

## Task 4: Rewrite `docs/index.md`

Last so the index can confidently link forward to the two pages that now exist.

**Files:**
- Modify (full rewrite): `docs/index.md`

- [ ] **Step 1: Replace the file contents**

Overwrite `docs/index.md` with:

````markdown
---
tags:
  - Apache Iceberg
  - Apache Kafka
  - Apache Polaris
  - Trino
  - Argo CD
  - OpenTelemetry
---
# Retail Lakehouse Platform

A self-hosted retail lakehouse that runs end-to-end on a single Mac, built to showcase three engineering disciplines side-by-side: Domain-Driven Design, streaming data infrastructure, and production-grade observability. Everything from the colima VM up to the Trino query engine is brought up by a single `task onboard` command.

## 💡 Highlights

=== "Software Engineering (DDD)"

    - 🏛️ **Strict Clean Architecture, enforced in CI** — `import-linter` blocks any dependency that crosses layers in the wrong direction (`adapter` → `application` → `domain`, no skipping).
    - 🧬 **Single image, three roles** — the same container runs as API, Scheduler, or Outbox publisher depending on the `GLAC_COMPONENT` env var, following 12-factor.
    - 📐 **Full DDD building blocks** — `AggregateRoot`, `ValueObject`, `DomainEvent`, `Repository`, and `Gateway` paired with an explicit outbound port-adapter naming convention (`{Aggregate}{Tech}Repo`, `{Verb}{Noun}{Tech}Gateway`).

=== "Data Engineering"

    - 🔄 **End-to-end CDC lakehouse** — MySQL → Debezium → Kafka → Iceberg sink with exactly-once delivery and automatic schema evolution.
    - 🏔️ **Iceberg + Polaris + MinIO** — a fully self-hosted REST-catalog lakehouse with no cloud dependency; the entire stack runs on local minikube.
    - 🔍 **Trino federated SQL** across Iceberg, BigQuery, and Faker catalogs, with OAuth2 SSO, fault-tolerant execution, and event listeners.

=== "Observability Engineering"

    - 📊 **Metrics** — `kube-prometheus` plus **Thanos** for long-term storage, backed by the same MinIO that serves the lakehouse.
    - 🔭 **Traces** — OpenTelemetry Operator handles auto-instrumentation; Jaeger receives traces from both Trino and Thanos.
    - 🏗️ **GitOps-native** — Argo CD `app-of-apps` deploys the entire platform from a single commit.

## 🏗️ Architecture

![](architecture.drawio.svg)
/// caption
Architecture Overview
///

![](trino-otel.drawio.svg)
/// caption
Architecture Overview — Observability Engineering
///

## 🚀 Try it yourself

Reproduce the whole platform on your own Mac in two steps: install the tools listed in [Prerequisites](prerequisites.md), then run the one-shot bootstrap in [Deployment](deployment.md).
````

- [ ] **Step 2: Verify the page renders**

Refresh `http://127.0.0.1:8000/` in the browser.

Expected:
- The h1 reads "Retail Lakehouse Platform"
- The Highlights section shows three tabs: "Software Engineering (DDD)", "Data Engineering", "Observability Engineering". Each tab has exactly three bullets with leading emoji and a bolded claim phrase.
- Both architecture SVGs render with their captions
- The "🚀 Try it yourself" links to `prerequisites.md` and `deployment.md` resolve
- mkdocs server log shows no broken links or missing-image warnings for index

- [ ] **Step 3: Commit**

```bash
git add docs/index.md
git commit -m "docs(index): refocus landing page on three engineering pillars"
```

---

## Task 5: Final cross-page verification

A quick whole-site sweep so we don't ship a broken nav or stray dangling reference.

**Files:** none modified — verification only.

- [ ] **Step 1: Smoke-test the nav order**

In the browser, confirm the left-hand nav lists, in this order at the top: `index.md` (rendered as the home link), `Prerequisites`, `Deployment`, `Argo CD`, then everything else as before.

- [ ] **Step 2: Check for build warnings**

Stop and restart `task serve-docs` so the build runs clean. Watch the terminal for `WARNING` lines.

Expected: zero warnings about `index.md`, `prerequisites.md`, `deployment.md`, or `mkdocs.yml`. Pre-existing warnings about other unrelated pages are fine — note them but don't fix here.

- [ ] **Step 3: Confirm no leftover references**

Run these searches and confirm each returns no hits in the three edited files:

```bash
grep -nE "AWS Glue|Amazon S3|kafka-cluster/$|prometheus-grafana" docs/index.md
grep -nE "colima start|minikube start" docs/prerequisites.md
```

Expected: both commands print nothing (exit code 1 from grep is fine).

- [ ] **Step 4: No commit needed**

This task only verifies. If anything failed, go back to the relevant earlier task, fix, and amend its commit only if the fix is trivial — otherwise add a follow-up commit.

---

## Self-Review Notes

- **Spec coverage:** every section of the spec maps to a task. `index.md` rewrite → Task 4. `prerequisites.md` rewrite → Task 3. `deployment.md` create → Task 2. `mkdocs.yml` nav update → Task 1. Cross-page sanity → Task 5.
- **Placeholder scan:** every code/markdown block is the actual content the engineer pastes. No "fill in details" or "similar to Task N".
- **Type consistency:** filenames, env vars, and Taskfile target names are spelled consistently across tasks (`KUBE_CONTEXT`, `DEPLOY_METHOD`, `task onboard`, `task offboard`, `task apps:validate`, `task serve-docs`).
- **Spec-vs-plan deltas:**
  - Spec listed `python@3.13` separately from `git`; plan groups them in the single `brew install` line per the spec's stated intent ("single brew install command listing all tools").
  - Spec mentioned a possible `## References` section per the writing-docs skill; the three pages here have no external references worth citing (they point inward to other project pages), so the section is omitted. The spec does not require it.
  - Spec mentioned the `k8s-env.excalidraw.svg` "moves with the manual setup section to deployment.md" — Task 2 does this.
