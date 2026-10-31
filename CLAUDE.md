# Project Guidelines

## Language

Respond in the same language as the user's message. The user typically communicates in Traditional Chinese (繁體中文) or English.

## Shell Commands

- Never use `cd` to change directory. Always use absolute paths or tool flags like `--directory`, `--project`.
- Use `uv run` instead of bare `python`, `python3`, `pytest`, or `pip`. Example: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -v`
- The local minikube/dev cluster context is `retail-lakehouse`. Infra scripts (`*/bootstrap.sh`, `*/validate.sh`, `*/patch.sh`) require `KUBE_CONTEXT` to be set explicitly — there is no fallback (scripts fail fast with `KUBE_CONTEXT is required`). Always pass it when invoking Taskfile entries or running scripts directly, e.g. `task onboard KUBE_CONTEXT=retail-lakehouse`.

## Project Status (snapshot 2026-10-24 — update as work lands)

**What it is:** an Iceberg lakehouse platform on minikube plus a self-built Table Maintenance service (`src/table-maintenance`, DDD + Clean Architecture) that schedules Iceberg maintenance (compaction, snapshot expiry). Long-term vision: "GitHub for Data" DataOps SaaS.

**Data flow:** MySQL →(Debezium CDC)→ Kafka →(Iceberg Sink)→ Iceberg on RustFS, catalog = Polaris → queried by Trino. Polaris catalog events →(Kafka event listener)→ Kafka topic `polaris-catalog-events` (key = event UUID, value = JSON; read it with `kafka-console-consumer.sh` in a broker pod or Kafka UI).

**History:**
- 2025-06 ~ 09: Trino, Kafka/Debezium/Iceberg CDC pipeline, monitoring stack.
- 2026-03 ~ 05: table-maintenance backend (API / scheduler / outbox messaging), naming conventions, import-linter layering.
- 2026-05 ~ 07: Polaris 1.5.0 + metrics reporter CDC to Kafka; Kafka 1 → 3 brokers; Iceberg sink static-membership fix; Kafka UI; Istio ambient (istiod / CNI / ztunnel) + Gateway API with wave-22 Gateway + HTTPRoutes; table-maintenance manifests moved `default` → `polaris` ns. An earlier "Polaris events via OTEL → Kafka" attempt was fully reverted.
- 2026-10: namespace re-layout (T1–T9); Polaris CDC removed (T10), Polaris upgraded 1.5.0 → 1.8.0 (T11), Polaris events published to Kafka via the Kafka event listener (T12), Temporal server deployed with a dedicated PostgreSQL (T13).
- 2026-10 ~ 10-24: table-maintenance control plane (plan Tasks 1–18): Temporal-based backend (API / worker / event consumer, Polaris catalog event hints, discovery, Spark maintenance jobs via the Spark operator) and the wave-25 Helm chart `table-maintenance` deployed on minikube; Task 19 e2e (`platform/25-lakehouse-control-plane/e2e.sh`, ADRs in `docs/adr/0001`–`0004`) ran all four Iceberg procedures SUCCEEDED on real Spark and compacted the `o'neil` partition through an escaped `where`; it surfaced and fixed `remove_orphan_files` listing (`prefix_listing => true`, c8ee993). Initiative done.
- 2026-10-26: Temporal workflows renamed `TableDiscoveryWorkflow` / `TableReconciliationWorkflow` / `TableMaintenanceWorkflow` / `TableMaintenanceAdmissionWorkflow` (setting `GLAC_ADMISSION_LIMIT`); IDs are `key=value` segments (`table-reconciliation:table-uuid=…`, `table-maintenance:table=…:run=…`, `table-maintenance-admission`, `table-discovery:catalog=…[:trigger=adhoc]`; table in the wave-25 README); maintenance runs store their `workflow_id` (result callback signals by it); every start sets a static summary.
- 2026-10-29: table-maintenance backend conformed to one layout (spec `docs/superpowers/specs/2026-10-29-backend-architecture-conformance-design.md`): aggregate axis in every layer, `adapter/{inbound,outbound,hybrid}` with Temporal as a hybrid adapter, no infrastructure terms in `application/`, boundary-only imports, 14 import-linter contracts with no `ignore_imports`, each enforced by `tests/architecture/`. Renames: `ManagedTable` → `Table`, `PolicyTemplate` → `TableMaintenancePreset`, `DiscoveryRule` → `TableDiscoveryRule`, `DiscoverySettings` → `TableDiscoverySettings`, `MaintenanceRun` → `TableMaintenanceRun` (run fields `workflow_id` → `execution_ref`, `spark_application` → `job_name`); API routes `/v1/table-maintenance-presets`, `/v1/table-discovery-rules`, `/v1/table-discovery-settings`, `/v1/table-maintenance-runs`; Workflow IDs unchanged.
- 2026-10-31: data platform console (spec `docs/superpowers/specs/2026-10-31-data-platform-console-design.md`): `src/console` (React + Vite, nginx image `console`) with table list, overview (health, storage, freshness), commits, maintenance runs, properties and settings; backend endpoints `GET /v1/tables/{uuid}/metadata`, `/commits`, `/health`, `/storage`; deployed in wave 25 behind `platform-gateway` at `/console/` (gateway `allowedRoutes` widened to `lakehouse-control-plane`); `e2e.sh` checks the endpoints against Trino's `$files` / `$snapshots`.
- 2026-10-31: console visual redesign (spec `docs/superpowers/specs/2026-10-31-console-visual-redesign-design.md`): Tailwind CSS v4 + shadcn/ui primitives in `src/console/src/components/ui/`, Geist / Geist Mono via fontsource, neutral design tokens with Light / Dark / System theme (`localStorage` key `console-theme`), app shell with sidebar, restyled table list, table page tabs, overview panels and settings; legacy `styles.css` removed and raw colours in feature code blocked by `noRawColors.test.ts`; UI rules in "Console UI" below.

**Cluster runtime (2026-10-24):** single minikube node on colima, container runtime `containerd` (was `docker` / cri-dockerd, whose cAdvisor series had no `container` label, so prometheus-adapter served no pod metrics) with `--cni bridge` pinned (with containerd minikube would pick kindnet, which enforces the kube-prometheus and Strimzi NetworkPolicies and blocks KEDA → Prometheus and Kafka UI → Connect REST). `kubectl top nodes` / `kubectl top pods -A` work through prometheus-adapter. `cluster:configure-registry-mirror` writes `/etc/containerd/certs.d/<registry ClusterIP>/hosts.toml` (HTTP) because containerd ignores the CIDR given to `--insecure-registry`; Strimzi KafkaConnect images are pulled from that ClusterIP.

**Deployed on minikube** (via `bootstrap-by-scripts`):
- Wave 10: cert-manager, kube-prometheus, Strimzi
- Wave 11: KEDA, Spark Operator, OTel Operator, Istio base, Gateway API CRDs
- Wave 12: istiod, istio-cni, ztunnel
- Wave 20: Kafka (3 brokers), RustFS, MySQL, Polaris DB, Jaeger (trino / thanos), temporal-db (creates the `temporal` namespace; PostgreSQL for Temporal)
- Wave 21–22: Temporal server (chart `temporalio/temporal` 1.7.0, server 1.32.0; frontend `temporal-frontend.temporal.svc.cluster.local:7233`, Web UI `temporal-web:8080`, Temporal namespace `default` with 3d retention), Polaris (also creates the `polaris-catalog-events` KafkaTopic in `kafka`), 2 KafkaConnectors (debezium-mysql, iceberg-sink), `platform-gateway` + HTTPRoutes
- Wave 23: Trino, Kafka UI
- Wave 25: lakehouse-control-plane (namespaces `lakehouse-control-plane`, `lakehouse-maintenance-operations`; Helm release `table-maintenance` = `table-maintenance-db` PostgreSQL, `migrate` Job, `api` (:8000), `worker`, `event-consumer`, `console` (nginx :8080, HTTPRoute `console` = `PathPrefix /console` on `platform-gateway`; open with `kubectl port-forward service/platform-gateway-istio 8080:80 --namespace istio-ingress` and browse `http://localhost:8080/console/`); images `table-maintenance-backend` / `table-maintenance-spark` / `console` built locally by `build.sh` and loaded into minikube; Spark jobs run in `lakehouse-maintenance-operations`, whose namespace is in the Spark operator `jobNamespaces`)

**Not deployed / on hold (do not touch unless the user re-opens them):**
- `platform/30-thanos`
- `platform/24-e2e-validation`
- ArgoCD path (`platform/00-argocd`, `01-argocd-health-checks`, `02-argocd-apps`, `charts/app-of-apps`)

**Current initiative: namespace re-layout** (one task at a time, each deployed + verified + committed on `main`; developer/reviewer agent prompts in `DEVELOPER_AGENT_PROMPT.md` / `REVIEWER_AGENT_PROMPT.md`):
1. `mysql`: `kafka-cdc` → `ecommerce-app` (done)
2. `kafka-cdc` → `kafka` (done)
3. `minio` → `object-storage` (done; the object store itself was later replaced by RustFS, see 9)
4. `polaris` → `lakehouse-catalog` (done)
5. `trino` → `lakehouse-query-engine` (done)
6. New wave `platform/25-lakehouse-control-plane` creates the `lakehouse-control-plane` + `lakehouse-maintenance-operations` namespaces (done; later the old `25-table-maintenance` / `25-tbl-maint-*` dirs were deleted and the table-maintenance control plane is deployed from this wave's Helm chart)
7. New wave `platform/20-temporal` creates the `temporal` namespace (renamed `20-temporal-db` in T13). (done)
   - 7.5: Replace Docker-Hub-removed minio/minio + minio/mc images with pinned pgsty/silo + pgsty/mc (done)
8. Full `task offboard` + `task onboard KUBE_CONTEXT=retail-lakehouse` end-to-end run (done; surfaced and fixed missing `istio-ingress` namespace in `22-polaris-routes`)
9. Replace pgsty Silo with RustFS: wave `20-minio` → `20-rustfs`, Service `rustfs` (S3 :9000), `rustfs-console`, image `rustfs/rustfs:1.0.3` (done; clean `offboard` + `onboard` passed in one run on 2026-10-23, CDC → Iceberg → Trino verified)

**Initiative: Polaris events via Kafka event listener** (done) (replaces the removed Polaris DB CDC):
- T10: Remove Polaris DB CDC (Debezium Postgres connector wave `22-kafka-debezium-polaris-connector`, its Kafka topics / replication slot / publication, `wal_level=logical` on polaris-db, Kafka UI entry) (done)
- T11: Upgrade Polaris to 1.8.0 (done; server `apache/polaris:1.8.0`, chart 1.8.0, bootstrap job `apache/polaris-admin-tool:1.8.0`, polaris-db Deployment now `strategy: Recreate`. Polaris 1.8.0 no longer creates the JDBC schema: the bootstrap Job has a `create-schema` init container running `CREATE SCHEMA IF NOT EXISTS polaris_schema` (chart sets `currentSchema=POLARIS_SCHEMA`, folded to lowercase). DB is schema v6; no auto-migration, so the DB was wiped and re-bootstrapped. After the wipe, `inventory.orders` was rebuilt by the Iceberg sink and only holds Kafka offset 37 onward; the older data files stay in RustFS as orphan files (a fresh onboard is not affected). The token-broker RSA key pair used to be regenerated on every Polaris restart, which invalidated the tokens held by the Iceberg sink / Trino ("Failed to verify the token"); it is now persisted in the `polaris-token-broker` Secret, which `21-polaris/bootstrap.sh` creates once if missing, so a Polaris restart no longer requires restarting the Connect pod. The first rollout that switches to the persisted key still needs one Connect pod restart)
- T12: Polaris events via Kafka event listener (done; `polaris.event-listener.types=kafka`, topic `polaris-catalog-events` 1 partition / 3 replicas, producer `bootstrap.servers=kafka-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092` (plain listener), producer `max.block.ms=5000` so a Kafka outage cannot stall Polaris for the 60 s default, all set under `advancedConfig`, effective at runtime. The OpenTelemetry listener was tried and dropped: it emits events only as OTel logs, the official image fixes `quarkus.otel.logs.enabled=false` at build time ("Build time property cannot be changed at runtime"), and `quarkus.otel.sdk.disabled` defaults to true, so no event ever reaches a collector)

**Initiative: Temporal** (done):
- T13: Temporal server in `temporal` ns (done; `platform/20-temporal-db` = namespace + `temporal-db` Postgres 17.11 (`postgres:17.11-alpine`) with Recreate strategy and plaintext dev Secret; `platform/21-temporal` = official chart 1.7.0, images server/admin-tools 1.32.0 and ui 2.54.1, 1 replica each, databases `temporal` / `temporal_visibility` with schema created by the chart's hook Jobs, `default` namespace created by the chart. Future table-maintenance workers connect to `temporal-frontend.temporal.svc.cluster.local:7233`)

**Known follow-ups:**
- `platform/21-polaris/bootstrap.sh` creates the `polaris-token-broker` Secret with a check that treats any `kubectl get` error (not just NotFound) as missing and uses `apply`, so a transient API error could regenerate the key pair. Make it NotFound-only plus `kubectl create` (as `25-lakehouse-control-plane/bootstrap.sh` does for `table-maintenance-db`).
- Worker and event-consumer pods have no liveness probes (deferred).
- Table maintenance control plane (wave 25): the migrate Job reruns on every `helm upgrade` (name carries the release revision); `helm upgrade --wait-for-jobs` waits for it and `validate.sh` asserts the current-revision Job completed; api / worker / event-consumer also gate on the seeded `default` table maintenance preset. The e2e tables `iceberg.e2e.tm_e2e_orders` / `tm_e2e_regions` and the rule `include iceberg / e2e / tm_e2e_*` stay in place (removal steps in the wave README).
- Node memory pressure (eased 2026-10-24): Trino now has memory limits (coordinator `-Xmx2G` / 2816Mi, worker `-Xmx3G` / 4Gi, jmx-exporter 384Mi) and KEDA scales workers 1 → 2 (max 2, 2 running queries per worker), so Trino uses ~5.3 GiB at 1 worker (was ~8 GiB idle and unbounded under load) and the node dropped from 75% to 64%. The earlier `<unknown>` HPA metric was not a KEDA misconfiguration: under memory pressure `prometheus-k8s-0` and `keda-operator-metrics-apiserver` restarted, and while the metric is unknown the HPA keeps its replica count. Concurrent Spark maintenance jobs under load were not re-tested.
- Spark result callback retries only 3 times 5 s apart (`runtime/spark/result_callback.py`); across a DB / Temporal outage the run is recorded from the polling fallback as `{"completed_without_callback": 1}` and the procedure metrics are lost. Widen the retry window or have the poller read the result from the driver.
- `rewrite_data_files` runs with `partial-progress.enabled=true`; the runtime now fails a CALL with failed and zero rewritten data files, but a lost callback still records success from the poller (`completed_without_callback`).
- Each SparkApplication downloads the Iceberg jars from Maven Central at submit; bake them into `table-maintenance-spark`.
- Event-driven runs with the `default` preset start while a writer is still committing; the 10-min discovery fallback was not exercised by the e2e (the event path found the tables first).
- `Table` (formerly `ManagedTable`) updates can be lost under concurrent writers: add a version column with compare-and-set.
- A retried `record_maintenance_operation_result` activity can lose the table's backoff update.
- The discovery enabled switch and the `table-discovery` schedule can drift until the worker restarts.
- Every CDC commit sends a hint that triggers a full metadata scan in the plan; debounce planning.
- No auth on the API or the Spark result callback, and no NetworkPolicy.
- Table maintenance uses the Polaris root principal; switch to a scoped principal.
- The running `table-maintenance-admission` workflow keeps the limit and lease it was started with; a changed `GLAC_ADMISSION_LIMIT` or lease applies only after it is restarted while idle.
- Catalog-wide sync re-ensures every live table's reconciliation workflow each run: one Temporal error aborts the rest of the sync (catch per table), and each wake costs a metadata scan (add start-without-signal).
- `TableReconciliationWorkflow` give-up changes have no `workflow.patched` guard; a history holding an old-code give-up would hit nondeterminism on replay. The give-up budget ignores admission-queue wait time.
- On-hold waves still reference pre-rename names (`minio-api.minio.svc`, `kafka-cdc`, `polaris`, `platform/20-minio`): `30-thanos`, `24-e2e-validation`, `charts/app-of-apps`. Fix when those are re-opened.
- Iceberg sink (Kafka 4.0 + sink 1.10) may commit "0 table(s)" for several minutes after a Connect pod start under low traffic; keep inserting and poll ~5–10 min when verifying snapshots.
- `bitnami/jmx-exporter` (Trino sidecar) is pinned by digest: Bitnami's free catalog only publishes `latest`, so bumping it means taking the new `latest` digest.
- NetworkPolicies are not enforced (bridge CNI). kube-prometheus and Strimzi ship policies that would block KEDA → `prometheus-k8s` and Kafka UI → Connect REST (:8083); before moving to an enforcing CNI (kindnet, Cilium, Calico), add allow rules for those paths.
- The containerd registry `hosts.toml` is keyed on the registry ClusterIP and written only by `task cluster:bootstrap`; if the `registry` Service is ever recreated, re-run `task cluster:configure-registry-mirror KUBE_CONTEXT=...`.

New namespaces are **not** labeled `istio.io/dataplane-mode=ambient` (no namespace is enrolled in the ambient mesh yet).

## Platform (Infra)

- `platform/<NN>-<component>/` — each wave dir has `bootstrap.sh` + `validate.sh` (some `patch.sh`); the `NN` prefix is the deploy order.
- `tasks/apps.yml` `bootstrap-by-scripts` / `validate` chain the waves; this is the active deploy path. `bootstrap-by-argocd` exists but is on hold.
- `task onboard` / `task offboard` create / destroy the whole colima + minikube cluster and run all waves.
- Kubernetes namespaces cannot be renamed: a "rename" means deploy into the new namespace, then delete the old one. Data loss on minikube is acceptable.

## Code Style

- **One object per file.** Each Python file exports one primary class, enum, or function. If a file grows to contain multiple exported objects, split it.
- **Descriptive filenames.** Name files after their primary export: `create_job.py` not `create.py`, `job_status.py` not `status.py`.
- **Package re-exports via `__init__.py`.** Expose a clean public API at the package level so consumers use `from models import JobRequest` instead of `from models.job_request import JobRequest`.
- **Intra-package: direct imports.** Within the same package, import from the module directly (e.g., `from models.job_status import JobStatus`) to avoid circular imports.
- **ABC over Protocol** for interface definitions. Use `abc.ABC` with `@abstractmethod`, not `typing.Protocol`.
- **StrEnum** for string-valued enumerations.
- **`from __future__ import annotations`** in every module for deferred type evaluation.

## Console UI

Rules for `src/console` pages (spec `docs/superpowers/specs/2026-10-31-console-visual-redesign-design.md`):

- **Build from `components/ui/` primitives.** Add a missing primitive with the shadcn CLI rather than hand-rolling one.
- **Token classes only.** Use tokens via Tailwind classes (`bg-background`, `text-muted-foreground`, `border-border`); no raw hex values or arbitrary colour classes (`[#…]`) in feature code (`src/components/` except `ui/`, `src/pages/`). Enforced by `src/test/noRawColors.test.ts`.
- **Colour only for status.** Neutral for everything else (including not due, cooldown, disabled); `warning` = due operation or truncated count; `destructive` = error or failed run; `success` = succeeded run only.
- **Identifiers in Geist Mono** (procedure names, snapshot ids, file paths, `execution_ref`, property keys / values, schema types); `tabular-nums` on number columns; sentence case, no all-caps labels.
- **No shadows on panels** (one subtle shadow on overlays only), no gradients, no entrance animations.

## Architecture Mindset

- **DDD best practices first.** Always prefer Domain-Driven Design idioms and patterns. When in doubt, choose the approach closest to established DDD literature (Evans, Vernon).
- **Design for high complexity.** This project will grow significantly in complexity. Favor extensible, well-structured designs over minimal implementations. Over-engineering is acceptable — under-engineering is not.

## Architecture: Clean Architecture (Strict Layering)

This project follows "Get Your Hands Dirty on Clean Architecture" with an additional **no-skip-layer rule**: each layer may only depend on the layer directly below it.

```
adapter/inbound  ──> application ──> domain
adapter/outbound ──> application ──> domain
adapter/hybrid   ──> application ──> domain
                     application ──> base (shared kernel)
adapter/*        ──✗──> domain (forbidden: must go through application)
```

Inside `application/` the order is `service` → `port` → `domain/service` → `domain/model`; a ring may import only rings below it, never above (contract `application-ring-order`).

### Backend Structure

One **aggregate axis** runs through every layer: each layer directory is split into the same aggregate directories (`table`, `table_discovery_rule`, `table_discovery_settings`, `table_maintenance_preset`, `table_maintenance_run`) plus `shared` for what spans aggregates.

```
backend/
├── bootstrap/                    # Composition roots (knows all layers)
│   ├── configs/                  # AppSettings, Component enum, adapter enums
│   ├── container/                # Wiring of services, ports and adapters
│   ├── api.py                    # GLAC_COMPONENT=api
│   ├── worker.py                 # GLAC_COMPONENT=worker (Temporal worker)
│   ├── event_consumer.py         # GLAC_COMPONENT=event_consumer
│   └── migrate.py                # GLAC_COMPONENT=migrate
├── adapter/                      # Outermost ring: inbound | outbound | hybrid
│   ├── inbound/
│   │   ├── web/{aggregate}/      # FastAPI routers, API DTOs
│   │   └── event_consumer/       # Polaris catalog event consumer loop
│   ├── outbound/{aggregate}/     # SQL, in-memory, catalog, Spark repo/store/gateway adapters
│   └── hybrid/                   # Technologies that are both directions
│       └── temporal/
│           ├── inbound/          # Workflows, activities, schedule setup
│           ├── outbound/{aggregate}/  # Signal, start and schedule gateways
│           └── contracts/        # Workflow names/IDs, signals, workflow inputs
├── application/                  # Middle ring
│   ├── domain/model/{aggregate}/ # Entities, Value Objects, Domain Events
│   ├── domain/service/{aggregate}/  # Domain services (planning, rule matching)
│   ├── port/inbound/{aggregate}/ # Use case interfaces + input/output types
│   ├── port/outbound/{aggregate}/  # Repo, Store and Gateway interfaces
│   ├── service/{aggregate}/      # Use case implementations
│   └── exceptions/               # Application-layer exceptions
├── base/                         # DDD shared kernel
├── entrypoint.py                 # GLAC_COMPONENT env var → api, worker, event_consumer, or migrate
└── tests/
```

### Rules

- **Domain** depends on nothing except `base/` and stdlib. No Pydantic — use dataclasses. Enforced by contract `domain-pure`.
- **Application** depends on domain and base, in ring order. No adapter, no bootstrap, no framework imports. Enforced by contracts `application-ring-order` and `application-no-outer-rings`.
- **Adapter** imports application only through ports and exceptions (not domain directly). Web adapter catches application-layer exceptions, not domain exceptions. Enforced by contract `adapters-see-only-ports`.
- **Adapter directions are independent.** `inbound`, `outbound` and `hybrid` do not import each other, a hybrid technology's `inbound` and `outbound` sides do not import each other, and inbound channels (`web`, `event_consumer`) are independent. Contracts `adapter-directions-separate`, `hybrid-directions-separate`, `inbound-channels-independent`. Layout: `tests/architecture/test_adapter_layout.py`.
- **Hybrid contracts** (`adapter/hybrid/<tech>/contracts/`) depend only on stdlib, base and ports, and only the same technology imports them. Contracts `hybrid-contracts-neutral`, `hybrid-contracts-private`. Temporal contracts are one package per workflow (`table_reconciliation`, `table_maintenance`, `table_maintenance_admission`, `table_discovery`) plus `shared` (task queue), each with short module names (`workflow_name.py`, `workflow_id.py`, `workflow_input.py`, `signal.py`, `activity.py`, `summary.py`); a signal lives with the workflow that receives it, an activity name with the workflow that calls it, and signal and activity names are StrEnums whose string values are pinned by `tests/adapter/hybrid/temporal/contracts/test_wire_names.py`. Temporal workflows import only Temporal and their contracts: contract `temporal-workflows-sandbox-safe`, plus `tests/architecture/test_temporal_workflow_sandbox.py` (Temporal's own sandbox validation) and `test_temporal_workflow_determinism.py`.
- **Adapters do not import bootstrap**, and **Configs** (`bootstrap/configs/`) is cross-cutting: it must not depend on any bounded context. Contracts `adapters-no-bootstrap`, `configs-leaf`. **Base** depends on nothing project-internal: contract `base-isolation`. **Application exceptions** are a leaf: they import no other application ring, adapter or bootstrap (contract `application-exceptions-leaf`).
- **Aggregate axis.** Every layer directory is split by the same aggregate names, with no loose modules at a layer root (only the web adapter's `create_app.py` and `error_handlers.py`). Enforced by `tests/architecture/test_aggregate_axis.py`. Adding an aggregate means updating `tests/architecture/aggregates.py`, `AGGREGATE_SQL_PACKAGES` in `adapter/outbound/shared/sql/create_schema.py` (guarded by `test_create_schema.py`) and any `.importlinter` paths.
- **Ports speak intent, not infrastructure.** Names in `application/` carry no infrastructure vocabulary (`temporal`, `workflow`, `signal`, `activity`, `spark`, `k8s`, `kubernetes`, `sql`, `pyiceberg`, `iceberg_rest`, `kafka`, `polaris`); a port names what the application wants (`SendTableChangeGateway` with a `TableChange`), the adapter picks the mechanism. Enforced by `tests/architecture/test_no_infrastructure_terms.py`.
- **Boundary-only imports.** A package with an `__init__.py` is a boundary; other packages import from it with `from <boundary> import Name`, never from a module inside it. Boundaries do not nest, and every module belongs to one (except the `bootstrap` entry modules `api`, `worker`, `event_consumer`, `migrate`). Enforced by `tests/architecture/test_import_boundary.py` (derived rules in `tests/architecture/boundaries.py`).
- **Import-linter has no exemptions.** `.importlinter` holds 14 named contracts and no `ignore_imports`. Enforced by `tests/architecture/test_importlinter_config.py`; run `lint-imports` to verify.
- **Naming and structure.** Inbound ports, outbound ports, services and web DTOs follow the naming tables below: `test_inbound_port_structure.py`, `test_outbound_port_structure.py`, `test_service_structure.py`, `test_dto_naming.py`; top-level layout `test_directory_structure.py`; inheritance depth `test_inheritance_depth.py`.
- **DTOs live in the adapter.** `CreateTableDiscoveryRuleApiRequest`/`TableDiscoveryRuleApiResponse` are in `adapter/inbound/web/table_discovery_rule/dto.py` with plain types (no domain enums).
- **Use case results live in the application layer.** Services convert domain objects to application-layer result dataclasses so adapters never see domain types.
- **Bootstrap** is the only layer allowed to import from all other layers. It is the composition root.
- **Single image, four components**: `GLAC_COMPONENT=api` (default), `worker`, `event_consumer`, or `migrate` via `entrypoint.py`.
- **Unified settings**: All configuration via `GLAC_` prefixed env vars (pydantic-settings). Nested with `__` delimiter: `GLAC_ADMISSION_LIMIT`, `GLAC_TEMPORAL__ADDRESS`.

## Development Workflow

- **TDD always.** Write the failing test first, watch it fail, write minimal code to pass, then refactor. No exceptions.
- **Verify before commit.** Every commit must pass: `pytest -v`, `ty check`, `ruff check .`, `lint-imports`.
- **Semantic commits.** Use conventional commits: `feat(scope):`, `fix(scope):`, `refactor(scope):`, `docs(scope):`.
- **Incremental, atomic commits.** Each commit is independently valid — tests pass, linter clean.
- **Taskfile for automation.** `task pre-pr` runs all checks (pre-commit + unit-test + arch-test).

## Project Vision

This is being built as a **multi-tenant SaaS** platform. The current bounded context is table maintenance (aggregates `Table`, `TableMaintenancePreset`, `TableDiscoveryRule`, `TableDiscoverySettings`, `TableMaintenanceRun`); customers and catalogs are planned next. Design decisions should consider future extensibility across bounded contexts.

## DDD Base Types (`base/`)

Shared kernel with zero external dependencies (stdlib only):
- `ValueObject` — frozen dataclass, equality by value
- `EntityId` — typed identifier (extends ValueObject)
- `Entity[ID]` — identity-based equality, `@dataclass(eq=False)`
- `AggregateRoot[ID]` — Entity + domain event collection
- `DomainEvent` — frozen dataclass with auto `occurred_at`
- `EventHandler[E]` — ABC for handling one domain event type
- `EventDispatcher` — concrete (non-subclassable) router from events to handlers
- `Repository[E]` — generic persistence ABC
- `Store` — infrastructure persistence (not aggregate)
- `Gateway` — external system interaction
- `UseCase[TInput, TOutput]` — single `execute()` method

## Outbound Port & Adapter Naming Convention

Three base classes define all outbound ports (in `base/`):

| Base Class | When to use | Port format | Adapter format |
|------------|------------|-------------|----------------|
| `Repository` | Aggregate persistence | `{Aggregate}Repo` | `{Aggregate}{Tech}Repo` |
| `Store` | Infrastructure persistence (not aggregate) | `{Noun}Store` | `{Noun}{Tech}Store` |
| `Gateway` | External system interaction | `{Verb}{Noun}Gateway` | `{Verb}{Noun}{Tech}Gateway` |

**Gateway verb vocabulary** (new verbs require review): `Read`, `Submit`, `Send`, `Publish`, `Poll`, `Sync`, `Write`, `Delete`, `Update`.

**Gateway directory structure** (under `port/outbound/{aggregate}/`):
```
{verb}_{noun}/
├── __init__.py       # re-export all symbols
├── gateway.py        # {Verb}{Noun}Gateway (extends Gateway)
├── input.py          # {Verb}{Noun}GatewayInput (optional, primitive-only)
└── output.py         # {Verb}{Noun}GatewayOutput (optional, primitive-only)
```

A gateway directory may also hold extra single-class files (for example `list_input.py`). Except `list_input.py`, which defines `{Verb}{Noun}GatewayListInput`, each defines one class named after its file stem in CamelCase (`{CamelCaseStem}`), primitive-only like `input.py`. Enforced by `test_outbound_port_structure.py` (the extra files used to be an allowlist of fixed names).

Input/output files must only use primitive types (`str`, `int`, `float`, `bool`, `dict`, `list`, `None`). They may import `base.value_object.ValueObject` but nothing from `application.domain` or other `base.*` modules. This is enforced by `test_outbound_port_structure.py`.

See `docs/superpowers/specs/2026-04-27-outbound-port-adapter-naming-convention.md` for full spec.

## DTO Naming Convention (Layer Suffixes)

Each DTO class carries a layer-specific suffix so its origin is unambiguous at a glance:

| Layer | File | Suffix | Example |
|-------|------|--------|---------|
| Inbound port | `port/inbound/{aggregate}/{verb}_{noun}/input.py` | `UseCaseInput` | `CreateJobUseCaseInput` |
| Inbound port | `port/inbound/{aggregate}/{verb}_{noun}/output.py` | `UseCaseOutput` (or `UseCaseOutputItem` for list helpers) | `CreateJobUseCaseOutput`, `ListJobsUseCaseOutputItem` |
| Outbound port | `port/outbound/{aggregate}/{verb}_{noun}/input.py` | `GatewayInput` | `SubmitJobRunGatewayInput` |
| Outbound port | `port/outbound/{aggregate}/{verb}_{noun}/output.py` | `GatewayOutput` | (none yet) |
| Web adapter | `adapter/inbound/web/{aggregate}/dto.py` | `ApiRequest` / `ApiResponse` | `CreateJobApiRequest`, `JobApiResponse` |

**Prefix rules:**
- Port layers (inbound/outbound): class prefix must match the PascalCase form of the parent directory name. Enforced by `test_inbound_port_structure.py` and `test_outbound_port_structure.py`.
- Web adapter: no prefix rule enforced. Verb prefix is convention for endpoint-specific request DTOs (e.g., `CreateJobApiRequest` over bare `JobApiRequest`); shared resource responses and nested sub-components may use noun-based names. Suffix enforced by `test_dto_naming.py`.

See `docs/superpowers/specs/2026-04-28-dto-naming-convention-design.md` for full spec.

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical roles, default strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

`docs/adr/` at the repo root. See `docs/agents/domain.md`.
