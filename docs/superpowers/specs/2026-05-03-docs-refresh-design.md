# Refresh top-level docs (index, prerequisites) and add deployment guide

## Background

`docs/index.md` and `docs/prerequisites.md` were written when the project was a smaller pipeline (Debezium + Kafka + Iceberg + Trino, with AWS Glue + S3 as the catalog/storage). The repo has since grown into a self-hosted, GitOps-driven platform on minikube, and both pages are now misleading on multiple fronts:

- `index.md` Highlights still describe AWS Glue + Amazon S3 as the catalog/storage layer; the project actually runs **Apache Polaris** (REST catalog) on **MinIO** (S3-compatible) with no cloud dependency.
- `index.md` is missing entire workstreams that exist in the repo: **Argo CD** (GitOps), **Spark** (Iceberg table maintenance), the **Observability stack** (kube-prometheus, Thanos, OpenTelemetry, Jaeger), **KEDA**, and the **`src/table-maintenance/` DDD backend**.
- `index.md` "What's Inside" shows an imagined `kafka-cluster/`, `mysql/`, … directory layout; the real layout is `platform/ charts/ src/ tasks/`.
- `index.md` "Deployment Steps" lists 7 manual steps and marks Spark / Prometheus as WIP, but the project now bootstraps everything end-to-end via `task onboard`.
- `prerequisites.md` lists only `colima docker kubectl minikube helm openjdk@21 jsonnet jsonnet-bundler` and walks through manual `colima start` + `minikube start` commands. The actual `task onboard` preconditions (`tasks/apps.yml`, `taskfile.yml`) require many more tools (`sops git python3 jb envsubst keytool npm uv`) and the manual cluster commands have been superseded by `task cluster:bootstrap`.

There is no top-level deployment guide — readers who want to reproduce the project must reverse-engineer it from `taskfile.yml` and `tasks/apps.yml`.

## Goals

- Reposition `docs/index.md` as a portfolio-style landing page: punchy highlights organized around three engineering pillars, plus the existing architecture diagrams. Anyone evaluating the repo should grasp the scope and depth in under two minutes.
- Reduce `docs/prerequisites.md` to a pure tools-installation page that matches the `task onboard` preconditions exactly. No cluster commands.
- Add a new `docs/deployment.md` (third in the nav, after `prerequisites.md`) that walks a reader from "tools installed" to "everything running and validated" using `task onboard`, and explains the platform layering and deploy-method choice.
- Keep the architecture diagrams (`architecture.drawio.svg`, `trino-otel.drawio.svg`) on the index page.
- Update `mkdocs.yml` nav to insert `deployment.md` between `prerequisites.md` and the `Argo CD` section.

## Non-Goals

- Rewrite or refresh the per-component deep-dive docs (`cdc/*`, `trino/*`, `polaris/*`, `minio/*`, `observability/**`, `iceberg/*`). They are linked from index/deployment but their content is out of scope.
- Update the architecture SVGs themselves. They are kept as-is; only the surrounding prose changes.
- Touch the `superpowers/` specs directory layout or any spec other than this design doc.
- Update `README.md`. It is misaligned (mentions Flink, PostgreSQL) but is a separate cleanup.
- Document `task offboard` beyond a one-liner; full teardown nuances are not the point of `deployment.md`.
- Add new troubleshooting content. Existing troubleshooting pages stay where they are and `deployment.md` does not link to them.

## Audiences and Voice

| Doc | Audience | Voice |
|-----|----------|-------|
| `index.md` | Portfolio reviewers, engineers evaluating the repo | Punchy, marketing-style highlights; one architecture-overview tone |
| `prerequisites.md` | Anyone who wants to reproduce the project locally on macOS | Terse, copy-pasteable; no narrative |
| `deployment.md` | Same reader as prerequisites, one step later | Step-by-step + a small amount of "why" for the layering and deploy-method choice |

## Design

### `docs/index.md` (rewritten)

Top-of-page tags and h1 stay. Replace everything below the h1.

**Sections, in order:**

1. **One-line product description** — replace the current "Retail Lakehouse with Debezium, Kafka, Iceberg, and Trino" framing with a sentence that emphasizes the platform/product angle (self-hosted retail lakehouse showcasing software, data, and observability engineering).
2. **💡 Highlights** — a `=== "<Pillar>"` tab block with **exactly three pillars**, each containing **exactly three bullets**. Bullets are punchy, marketing-style, with a leading emoji per bullet:
   - **Software Engineering (DDD)**
     - 🏛️ Strict Clean Architecture; dependency direction enforced in CI by `import-linter` (adapter → application → domain, no skipping).
     - 🧬 Single image, three roles — same container runs API / Scheduler / Outbox publisher selected by `GLAC_COMPONENT` (12-factor).
     - 📐 Full DDD building blocks — `AggregateRoot`, `ValueObject`, `DomainEvent`, `Repository`, `Gateway` — paired with an explicit outbound port-adapter naming convention (`{Aggregate}{Tech}Repo`, `{Verb}{Noun}{Tech}Gateway`).
   - **Data Engineering**
     - 🔄 End-to-end CDC lakehouse — MySQL → Debezium → Kafka → Iceberg sink with exactly-once delivery and automatic schema evolution.
     - 🏔️ Iceberg + Polaris + MinIO — fully self-hosted REST catalog lakehouse with no cloud dependency, runs end-to-end on local minikube.
     - 🔍 Trino federated SQL across Iceberg / BigQuery / Faker catalogs, with OAuth2 SSO, fault-tolerant execution, and event listeners.
   - **Observability Engineering**
     - 📊 Metrics — kube-prometheus + **Thanos** for long-term storage (object store backed by the same MinIO).
     - 🔭 Traces — OpenTelemetry Operator for auto-instrumentation; Jaeger receives traces from both Trino and Thanos.
     - 🏗️ GitOps-native — Argo CD app-of-apps deploys the whole stack from a single commit.
3. **🏗️ Architecture** — keep both existing images and captions:
   - `architecture.drawio.svg` (Architecture Overview)
   - `trino-otel.drawio.svg` (Architecture Overview — Observability Engineering)
4. **🚀 Try it yourself** — a short closing block: one sentence pointing to `prerequisites.md` for tool installation and `deployment.md` for the one-shot bootstrap.

**Removed sections** (do not migrate elsewhere unless noted):

- The five-tab original "Highlights" (Debezium / Kafka / Iceberg Sink / Iceberg Lakehouse / Trino) — replaced by the three pillars above.
- "🗂️ What's Inside?" — removed entirely. The directory listing it shows is fictional anyway.
- "📑 Deployment Steps" — removed. Its intent is replaced by the new `deployment.md`.

### `docs/prerequisites.md` (rewritten)

**Sections, in order:**

1. **Hardware** — keep the Mac mini (2024) spec block as-is. It tells readers what resources to expect to need.
2. **Install required tools via Homebrew** — single `brew install` command listing all tools the `task onboard` preconditions check for. Source of truth is `taskfile.yml` (lines ~50–98) and `tasks/apps.yml` (lines ~13–27). The full list:
   - `colima docker kubectl minikube helm sops git python@3.13 jsonnet jsonnet-bundler gettext openjdk@21 node uv`
   - One sentence per non-obvious tool explaining why (e.g. `gettext` provides `envsubst`; `openjdk@21` provides `keytool`).
3. **Next step** — one line: "Tools installed? Continue to [Deployment](deployment.md)."

**Removed sections:**

- "Setting Up a Local Kubernetes Cluster" — the manual `colima start` and `minikube start` commands move into `deployment.md` § 3 as part of the "what `task cluster:bootstrap` does for you" explanation.
- The `assets/k8s-env.excalidraw.svg` reference — moves with the manual setup section to `deployment.md`.

### `docs/deployment.md` (new file)

**Sections, in order:**

1. **Quick start (TL;DR)** — three lines:
   - Pick a kube context name (e.g. `retail-lakehouse`).
   - Run `task onboard KUBE_CONTEXT=retail-lakehouse DEPLOY_METHOD=argocd`.
   - Wait 10–20 minutes; the cluster, all platform apps, and the local dev environment will be ready.
2. **Choose a deploy method** — short comparison table of the two `DEPLOY_METHOD` values:

   | Method | What it does | When to pick it |
   |--------|--------------|-----------------|
   | `scripts` | Runs each `platform/*/bootstrap.sh` directly in dependency order | First-time exploration; easier to read failures step-by-step |
   | `argocd` | Bootstraps Argo CD, then applies the app-of-apps manifest | Recommended; mirrors a real GitOps workflow and gives a UI to inspect drift/health |
3. **What `task onboard` does** — three subsections, in execution order:
   1. **`cluster:bootstrap`** — provisions the colima VM and the minikube cluster. Show the equivalent `colima start` and `minikube start` commands (moved here from `prerequisites.md`) so readers understand what's happening, and reference the `k8s-env.excalidraw.svg` diagram. Mention the defaults (`CPU=9`, `MEMORY=28`, `DISK_SIZE=120`) and that they can be overridden as Taskfile vars.
   2. **`apps:bootstrap-by-{scripts|argocd}`** — points at § 4 below for the layering rationale. Notes that the picked deploy method drives which script path runs.
   3. **`dev:sync`** — sets up local Python (uv), Node (npm), and pre-commit hooks so the repo is ready for development.
4. **Platform layering (10 / 20 / 21 / 22 / 23)** — explain that `platform/` is numbered to encode dependency tiers. Use a small table:

   | Prefix | Tier | Examples |
   |--------|------|----------|
   | `00` | Argo CD itself (only used in `argocd` method) | `00-argocd`, `01-argocd-health-checks`, `02-argocd-apps` |
   | `10` | Cluster-wide operators / control planes | `10-cert-manager`, `10-kube-prometheus`, `10-strimzi-operator` |
   | `11` | Additional operators that depend on tier 10 | `11-keda`, `11-spark-operator`, `11-otel-operator` |
   | `20` | Stateful infra and standalone services | `20-kafka-cluster`, `20-mysql`, `20-minio`, `20-jaeger-thanos`, `20-jaeger-trino`, `20-polaris-db` |
   | `21` | Apps consuming tier-20 services | `21-polaris`, `21-kafka-debezium-mysql-connector` |
   | `22` | Apps consuming tier-21 outputs | `22-kafka-iceberg-connector` |
   | `23` | Top-level query/UX layer | `23-trino` |
   | `25` | Application backend (table maintenance) | `25-tbl-maint-db`, `25-tbl-maint-bcknd`, `25-tbl-maint-schdlr` |
   | `30` | Cross-cutting layer above everything | `30-thanos` |

   One short paragraph after the table: "lower numbers must be ready before higher numbers; this ordering is what `bootstrap-by-scripts` walks, and what the Argo CD app-of-apps encodes via sync waves."
5. **Validate** — one command: `task apps:validate KUBE_CONTEXT=retail-lakehouse`. Mention it runs all per-app `validate.sh` scripts in parallel.
6. **Tear down** — one command: `task offboard KUBE_CONTEXT=retail-lakehouse`. One sentence: deletes the minikube cluster and the colima VM (no-op if absent).

No troubleshooting section. No links to per-component deep-dive docs from this page (the nav already exposes them).

### `mkdocs.yml`

Insert one line in `nav:` between `prerequisites.md` and the `Argo CD` group:

```yaml
nav:
  - index.md
  - prerequisites.md
  - deployment.md       # new
  - Argo CD:
    - argocd/deployment.md
    ...
```

No other nav changes. No theme / plugin / extension changes.

## Sources of Truth

When writing the docs, treat these files as authoritative. If anything in the prose contradicts them, the prose is wrong.

- Tools list: `taskfile.yml` `onboard.preconditions` (lines ~50–98) and `tasks/apps.yml` `bootstrap.preconditions` (lines ~13–33).
- `task onboard` behavior and var defaults: `taskfile.yml` `onboard:` (lines ~99–125).
- `cluster:bootstrap` actual commands: `tasks/cluster.yml` (read at write-time).
- Platform layering: directory listing of `platform/` (already gathered above).
- Deploy-method scripts: `tasks/apps.yml` `bootstrap-by-scripts` and `bootstrap-by-argocd` (lines ~39–109).
- Validate behavior: `tasks/apps.yml` `validate:` (lines ~111–165).
- Offboard behavior: `taskfile.yml` `offboard:` (lines ~127–144).

## Acceptance Criteria

- `docs/index.md` no longer mentions AWS Glue, Amazon S3 as a primary store, the fictional `kafka-cluster/ mysql/ …` directory layout, or the seven-step manual deployment list.
- `docs/index.md` Highlights has exactly three pillar tabs, each with exactly three bullets, and both architecture SVGs render.
- `docs/prerequisites.md` contains no `colima start` or `minikube start` commands. Its `brew install` line covers every tool the `task onboard` preconditions check.
- `docs/deployment.md` exists with the six sections above and ends at "Tear down" — no troubleshooting section.
- `mkdocs.yml` nav lists `deployment.md` immediately after `prerequisites.md`.
- `task serve-docs` renders all three pages without broken links or missing images.

## Out-of-Scope Follow-ups (noted, not done here)

- `README.md` still references Flink and PostgreSQL — needs its own pass.
- Per-component deep-dive docs may have similar drift; will be revisited individually.
