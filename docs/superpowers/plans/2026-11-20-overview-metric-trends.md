# Overview Metric Trends Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every reconcile keeps the newest metrics of a managed table in the database, the API exports them in the Prometheus text format to a small Prometheus, and the table page's Overview shows the current values as cards and their 1, 3 or 6 hour trends as charts, which the backend reads from Prometheus for the console.

**Architecture:** The reconcile's plan step already observes the table; a domain service turns that observation into a `TableMetrics` value object, which a new `TableMetricsStore` keeps (one row per table, forward-only, removed when the plan skips the table). The API serves those rows at `GET /v1/table-metrics` (exporter pattern, like kube-state-metrics), a new wave-26 Prometheus scrapes it every 30 s and keeps 6 hours, and `GET /v1/tables/{uuid}/metrics?range=` asks Prometheus `query_range` with one fixed selector through a new `ReadTableMetricHistoryGateway`. The console's Overview builds the dashboard from the design system's `MetricCard`, `LineChart`, `AreaChart` and `TimeRangePicker`.

**Tech Stack:** Python 3.14, Pydantic, SQLAlchemy Core, FastAPI, PyIceberg 0.11.1, httpx (already a dependency), Temporal Python SDK (unchanged workflows), Prometheus v3.5.0 (`quay.io/prometheus/prometheus:v3.5.0`, plain manifests), React + TanStack Query + orval, `@retail-lakehouse/design-system` chart widgets (KCL-90).

**Spec:** Linear KCL-96 (https://linear.app/kcl10/issue/KCL-96, no comments), with the decisions in the KCL-69 comments of 2026-11-17 and 2026-11-19 (metric list, exporter pattern, 6 h retention, backend-proxied `query_range`, dashboard layout) and the design-system story `Patterns/Table metrics dashboard` (`src/design-system/src/stories/MetricsDashboard.stories.tsx`).

**Refreshed 2026-11-20 against HEAD `bfdc0987`** (KCL-93 and KCL-91 built). **Order:** this plan is implemented first, then KCL-97 (`docs/superpowers/plans/2026-11-20-schema-version-diff.md`), which builds on this plan's versions of the files both change. **Read each file at HEAD before changing it; never apply a step against a remembered version.**

## Global Constraints

- **Builds on KCL-93 and KCL-91, both built (refreshed 2026-11-20).** Compaction rounds, candidates, admission, scheduler settings, `/v1/compaction-rounds*`, `/v1/scheduler-settings`, `/v1/tables/{uuid}/compaction-candidates`, the Compaction Rounds page and the Candidates tab are gone; `/v1/platform-settings` is served by `platform_settings_router` in `TM/adapter/inbound/web/table_maintenance_run/`. A policy is `description`, `on` (`schedule.every_seconds` + optional `catalog_commit.debounce_seconds`), `dry_run` and four optional `{target, options}` blocks; cooldowns are platform settings (`OperationCooldowns`, passed to the plan service as `cooldowns=`); a table is checked on its schedule, when a catalog commit window closes, and always for `manual_run`, `reconcile_now`, `policy_changed` and `table_managed`, while `table_seen` plans nothing. Nothing here reads the policy shape or the wake reasons. The candidate sync and `candidates_repo.delete_by_table` no longer exist, so the metrics calls in `PlanTableMaintenanceService.execute` (`TM/application/service/table/plan_table_maintenance.py`) are new lines at these places:
  - **save:** right after `self._record_last_commit(table, observation.last_committed_at)`, inside the `with translate_domain_errors():` block and before `self._lift_stale_marks(...)`, so it runs for manual and scheduled plans, dry run or not (`policy.dry_run` only empties the plan later);
  - **delete** (one private helper `_forget_metrics(table_uuid: str)`, called before each `return`): `return _skip_unknown_table()` (no table in the repo), `return _skip(reason, applied, policy, table, manual_priority)` (status `dropped` or `unmanaged`, from `_SKIP_REASONS`), and `return _skip("not_found", ...)` (no observation, or one with another uuid). These are all the skip returns at HEAD.
- **The metrics store is a required keyword of the plan service (refreshed 2026-11-20).** `PlanTableMaintenanceService(tables_repo, catalog_gateway, resolve_applicable_policy, *, metrics_store: TableMetricsStore, cooldowns=DEFAULT_OPERATION_COOLDOWNS)`. Every construction passes it: `build_use_cases.py`, `tests/context/table_maintenance/fakes/plan_service_on_fakes.py` (gains `metrics_store: TableMetricsStore | None = None`, an `InMemoryTableMetricsStore()` when none is given, so its other callers stay unchanged) and the two direct constructions in `test_plan_uses_the_injected_cooldowns`. `Repositories` (`bootstrap/container/repositories.py`, "one repository per aggregate") gains `table_metrics: TableMetricsStore` and its docstring says it also holds the table metrics store.
- **Metric names and series (Prometheus naming, all gauges, no timestamps in the exposition, base units):**
  - `iceberg_table_info{table_uuid, catalog, namespace, table} 1` (names live only here, kube-state-metrics' `_info` pattern, so a rename does not split the other series)
  - `iceberg_table_observed_timestamp_seconds{table_uuid}` (when the reconcile observed the table)
  - `iceberg_table_files{table_uuid, content="data"|"position_delete"|"equality_delete"|"deletion_vector"}` (summing over `content` gives every live file)
  - `iceberg_table_data_size_bytes`, `iceberg_table_data_records`, `iceberg_table_position_delete_records`, `iceberg_table_equality_delete_records`, `iceberg_table_reducible_files`, `iceberg_table_manifests`, `iceberg_table_manifests_size_bytes`, `iceberg_table_snapshots` (each `{table_uuid}`)
  - `iceberg_table_manifest_entries{table_uuid, status="added"|"existing"|"deleted"}`
  - 17 series per table; only tables whose status is `managed` are exported.
- **Definitions:** "Total rows" is the sum of data files' record counts (Iceberg's own `total-records`, the number the table header shows); rows after deletes are not computed, because equality deletes make that unknowable from metadata (Iceberg leaves partition stats' `total_record_count` null for the same reason). `position_delete` files exclude deletion vectors (position-delete entries whose `file_format` is `PUFFIN`); `position_delete_records` include the deletion vectors' record counts. Reducible files are the table total of the existing `compute_reducible_files` (`TM/application/domain/service/table/compute_reducible_files.py`) over every partition at `resolve_target_file_size(observation.properties)` (`TM/application/domain/service/shared/resolve_target_file_size.py`: the table's `write.target-file-size-bytes`, else 512 MiB), whatever the policy's `rewrite_data_files.target.per` and even when the policy has no `rewrite_data_files` block: the number `assess_maintenance._measure_compaction` reports for `per: table` (refreshed 2026-11-20: under `per: partition` the check's `reducible_files` measurement sums only the partitions over `at_most`, so the Reconciliations tab and the card may differ there; the card is the table's state, not a check). Manifests are every manifest of the current snapshot (data and delete); entry counts come from the manifest list's `added_files_count` / `existing_files_count` / `deleted_files_count` (`None` → 0).
- **Endpoints:**
  - `GET /v1/table-metrics` → `text/plain; version=0.0.4; charset=utf-8`, `include_in_schema=False` (Prometheus is its only caller; it stays out of the console's client).
  - `GET /v1/tables/{table_uuid}/metrics/current` → `TableCurrentMetricsApiResponse`; 404 for an unknown table; 200 with `observed_at: null` and `metrics: null` for a known table with no row (not reconciled yet, or not managed).
  - `GET /v1/tables/{table_uuid}/metrics?range=1h|3h|6h` (default `6h`, anything else 422) → `TableMetricTrendsApiResponse`; 404 for an unknown table; 502 with the reason when Prometheus cannot answer.
  - `GET /v1/tables/{uuid}/health` and `/storage` are removed with their use cases, ports, DTOs, `measure_storage`, `storage_measure_mapper.py` and `TableStorageMeasure` (no console caller).
- **Ranges and steps:** `1h` step 30 s, `3h` step 90 s, `6h` step 180 s (120 steps, so 121 points each); `end` = now rounded down to the step, `start` = `end − range`; one point per step from `start` to `end` inclusive, a value is `null` where Prometheus has none. Trend keys are the `TableMetrics` count field names plus two derived: `manifest_average_size_bytes` (`manifests_size_bytes / manifests`) and `manifest_average_entries` (all entries / `manifests`), both `null` when `manifests` is 0 or missing.
- **One fixed query:** `{__name__=~"iceberg_table_.+", table_uuid="<uuid>"}` (the uuid escaped as a PromQL string: `\` → `\\`, `"` → `\"`, newline → `\n`), sent only for a uuid the tables repo knows. No PromQL from the client.
- **Prometheus (wave `platform/26-table-metrics-prometheus`, namespace `table-metrics`, ambient):** plain manifests (ConfigMap, PVC 2Gi, Deployment with `Recreate`, ClusterIP Service `table-metrics-prometheus:9090`, no HTTPRoute: never exposed); image `quay.io/prometheus/prometheus:v3.5.0`; args `--storage.tsdb.retention.time=6h`, `--storage.tsdb.retention.size=1GB`; requests `cpu: 50m`, `memory: 256Mi`, limit `memory: 1Gi`; `scrape_interval: 30s`, `scrape_timeout: 10s`; one job `table-maintenance-api`, `metrics_path: /v1/table-metrics`, static target `table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000` (one target, so several API replicas never duplicate series; every replica reads the same database). Labels on every object: `app.kubernetes.io/name: prometheus`, `app.kubernetes.io/instance: table-metrics-prometheus`, `app.kubernetes.io/part-of: table-maintenance`, `app.kubernetes.io/component: metrics-store`, `app.kubernetes.io/managed-by: kubectl`; the pod template adds `app.kubernetes.io/version: v3.5.0`; selectors use only `name` + `instance`. The paused `10-kube-prometheus` stays paused. **Fit with the platform (checked 2026-11-20 against `platform/CLAUDE.md`):** wave 26 runs right after wave 25 (the API it scrapes) and before the on-hold `30-thanos`, chained in `tasks/apps.yml` like wave 25 (`bootstrap-by-scripts` `status` and `cmds`, both `validate` lists); `table-metrics` is an application namespace, so it is ambient (created with `namespace::apply_ambient`, asserted with `namespace::assert_ambient` and `mesh::assert_hbone` from `scripts/utils/namespace.sh`), unlike `monitoring`, which stays outside the mesh only for kube-prometheus to diagnose a broken mesh; the scrape is HBONE between two ambient namespaces, and `validate.sh`'s API-server proxy calls come from outside the mesh as plaintext under the permissive default. No `gateway::allow_routes` (no HTTPRoute). The 256Mi request fits in the memory the Trino pause freed (KCL-89).
- **Cluster access (refreshed 2026-11-20).** Wave 13 gates every gateway path but `/polaris` behind a Keycloak session, so API checks through the gateway use `gateway::curl <path>` (source `scripts/utils/gateway.sh` with `KUBE_CONTEXT=retail-lakehouse`; it gets a `platform-validate` token), and the console at `http://localhost:8591/console/` logs in as `platform-admin` (password in Secret `identity/keycloak-clients`). The in-cluster scrape goes straight to the Service, not through the gateway, so it is not gated.
- **Backend setting:** `GLAC_METRICS__PROMETHEUS_URL` (default `http://table-metrics-prometheus.table-metrics.svc.cluster.local:9090`), `GLAC_METRICS__QUERY_TIMEOUT_SECONDS` (default `10`).
- **Console:** the dashboard shows only for a managed table, above the Table and policy panels. Cards, in order: Data files, Total size, Total rows, Reducible files, Snapshots, Manifests (values from `/metrics/current`; delta and sparkline from the trend, always `tone: "neutral"`, since status colours are for status only). Sections: Files (4 series), Size (`AreaChart`), Rows (3 series), Reducible files, Manifests (one chart of manifests and entries per manifest, one of average manifest size), Snapshots. Ranges `1h`, `3h`, `6h`, default `6h`, kept in the url as `?range=` with `replace` navigation (the default keeps the url clean). Both queries refetch every 60 s. The Table panel drops its Rows, Data files and Size rows, which the header and the cards already show (closes the follow-up "The Overview Table panel repeats rows, data files and size").
- No new dependency (backend or console). No data migration: `create_schema` creates the new table; the cluster is rebuilt. No Temporal workflow changes, so no `workflow.patched`.
- Follow `CLAUDE.md`: TDD, one object per file, `from __future__ import annotations`, StrEnum, ABC ports, `uv run`, never `cd`, kubectl verb first, never `--no-verify`, never two test suites at once, explicit paths in `git add`. Every commit passes `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend` (or `scope=frontend`, or `scope=all` when both sides change); a backend change to the API regenerates the client with `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api` and commits it in the same commit.
- Commit messages end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.

## Review Focus

- A reconcile retried with an older observation (Temporal retries the plan activity after a newer one landed) never replaces newer metrics: the store only moves `observed_at` forward.
- A table that leaves maintenance while its reconciliation workflow is gone (so no plan runs to delete its row) disappears from `/v1/table-metrics` anyway, because the exporter keeps only managed tables; its Prometheus series then go stale.
- A label value holding `"`, `\` or a newline (a namespace or table name) is escaped in the exposition and in the PromQL selector, so neither breaks the scrape nor the query.
- Prometheus returns `NaN`, `+Inf` or a gap: the trend shows `null`, never a 500; a Prometheus that is down or answers `"status": "error"` gives 502 with its reason, and the cards (from the database) still show.
- A table with no snapshot (created, never written) gets all-zero metrics, not a skip; a table with zero manifests gets `null` averages, not a division error.
- Metrics move only when a plan runs: on the policy's `on.schedule` (the default policy: every 3600 s), when a commit window closes (`on.catalog_commit`, default 300 s after the first unchecked commit), and on a manual run, `reconcile_now`, `policy_changed` or `table_managed`; never on `table_seen`. A 1 h chart of a table whose policy has no `catalog_commit` can be a flat line, which is expected.

---

## File Structure

Backend paths are relative to `src/data-platform/backend/`; `TM` = `context/table_maintenance`, tests mirror under `tests/`.

| File | Responsibility |
|---|---|
| `TM/application/domain/model/shared/partition_stats.py`, `manifest_stats.py` | record counts, deletion vectors, manifest entry counts |
| `TM/application/port/outbound/table/read_table_metadata/table_metadata_observation.py`, `TM/adapter/outbound/table/pyiceberg/observation_mapper.py`, `TM/application/service/table/table_observation_from_gateway.py` | carry the new counts |
| `TM/application/domain/model/table/table_metrics.py` (new) | `TableMetrics` value object |
| `TM/application/domain/model/table/metric_time_range.py` (new) | `MetricTimeRange` StrEnum with duration and step |
| `TM/application/domain/service/table/measure_table.py` (new) | observation → `TableMetrics` |
| `TM/application/domain/service/table/derive_metric_trend_values.py` (new) | the two manifest averages |
| `TM/application/port/outbound/table/table_metrics_store.py` (new) | `TableMetricsStore` port |
| `TM/adapter/outbound/table/sql/table_metrics_table.py`, `table_metrics_row_mapper.py`, `table_metrics_sql_store.py` (new), `TM/adapter/outbound/table/sql/__init__.py` | SQL store; the package export registers the table for `create_schema` |
| `TM/application/service/table/plan_table_maintenance.py`, `tests/context/table_maintenance/fakes/plan_service_on_fakes.py`, `tests/context/table_maintenance/fakes/in_memory_table_metrics_store.py` (new) | save on observe, delete on skip |
| `TM/application/port/inbound/table/{list_table_metrics,get_table_current_metrics,get_table_metric_trends}/` (new), `TM/application/service/table/{list_table_metrics,get_table_current_metrics,get_table_metric_trends}.py` (new) | the three use cases |
| `TM/application/port/outbound/table/read_table_metric_history/` (new) | `ReadTableMetricHistoryGateway`, input, output, `metric_history_unavailable_error.py` |
| `TM/adapter/outbound/table/prometheus/` (new) | `ReadTableMetricHistoryPrometheusGateway`, `promql_string.py` |
| `TM/adapter/inbound/web/table/table_metrics_router.py`, `table_metrics_exposition.py` (new), `router.py`, `dto.py`, `error_handlers.py`, `register_routes.py` | routes and DTOs |
| `bootstrap/configs/metrics_settings.py` (new), `app_settings.py`, `bootstrap/container/*` | wiring |
| `platform/26-table-metrics-prometheus/` (new), `tasks/apps.yml`, `platform/25-lakehouse-control-plane/chart/{values.yaml,templates/configmap.yaml}` | Prometheus and the env var |
| `src/data-platform/frontend/src/components/TableMetricsDashboard.tsx` (new) + `.test.tsx` + `.stories.tsx`, `src/lib/metricTrendRows.ts` (new) + test, `src/components/tabs/useMetricRange.ts` (new), `components/tabs/OverviewTab.tsx`, `src/stories/{storyData,lakehouseHandlers}.ts`, `pages/TablePage.test.tsx`, `pages/TablePage.stories.tsx` | console (KCL-97 later changes the last four again, on top of this plan's versions) |
| `docs/adr/0013-table-metrics-in-the-database-and-prometheus.md` (new) and the docs | record the decision |

---

### Task 1: The observation counts records, deletion vectors and manifest entries

**Files:**
- Modify: `TM/application/domain/model/shared/partition_stats.py`, `TM/application/domain/model/shared/manifest_stats.py`, `TM/application/port/outbound/table/read_table_metadata/table_metadata_observation.py` (docstring keys), `TM/adapter/outbound/table/pyiceberg/observation_mapper.py`, `TM/application/service/table/table_observation_from_gateway.py`
- Test: `tests/context/table_maintenance/adapter/outbound/table/pyiceberg/test_observation_mapper.py`, `test_observation_mapper_delete_files.py`, `test_read_table_metadata_pyiceberg_gateway.py`, the converter's test `tests/context/table_maintenance/application/service/table/test_table_observation_from_gateway.py`, and `tests/context/table_maintenance/application/domain/model/shared/test_table_observation.py` (the negative-count test); `test_compute_reducible_files.py` and `test_assess_maintenance.py` stay green unchanged

**Interfaces:**
- Produces: `PartitionStats` gains `data_record_count: int = 0`, `position_delete_record_count: int = 0`, `equality_delete_record_count: int = 0`, `deletion_vector_count: int = 0` (all `>= 0`); `position_delete_file_count` keeps counting deletion vectors, so compaction's reducible files do not change. `ManifestStats` gains `added_entries: int = 0`, `existing_entries: int = 0`, `deleted_entries: int = 0`. Gateway partition items gain the keys `data_record_count`, `position_delete_record_count`, `equality_delete_record_count`, `deletion_vector_count`; manifest items `added_entries`, `existing_entries`, `deleted_entries`. The converter reads the new keys with `.get(key, 0)` (documented), so observations built without them still convert.

- [ ] **Step 1: Write the failing tests**

```python
def test_observe_counts_data_records_per_partition(catalog, gateway): ...
    # append 3 rows on day 1 and 2 rows on day 2 → the two partitions carry data_record_count 3 and 2

def test_observe_counts_manifest_entries(catalog, gateway): ...
    # two appends → two manifests; each has added_entries 1, existing 0, deleted 0

def test_deletion_vectors_are_counted_apart(): ...
    # as test_observation_mapper_delete_files builds entries: one PARQUET position delete (record_count 4)
    # and one PUFFIN position delete (record_count 6) in one partition →
    # position_delete_file_count 2, deletion_vector_count 1, position_delete_record_count 10

def test_equality_delete_records_are_summed(): ...  # two equality delete files of 2 and 5 records → 7

def test_converter_defaults_missing_counts_to_zero(): ...  # a partition item without the new keys → all 0

def test_negative_record_count_is_refused(): ...  # PartitionStats(data_record_count=-1, ...) → InvariantViolation
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/adapter/outbound/table/pyiceberg tests/context/table_maintenance/application -k "record or manifest_entries or deletion_vector or missing_counts" -v`
Expected: FAIL, unknown field `data_record_count`.

- [ ] **Step 3: Implement.** In `observation_mapper._partition_stats(table, manifest_files)` add per-key counters for `data_file.record_count` by content and count `content == POSITION_DELETES and data_file.file_format == FileFormat.PUFFIN` as a deletion vector; manifests come from the `manifest_files = snapshot.manifests(table.io)` that `observation_from_table` already reads (today each item is `{"length_bytes": m.manifest_length}`), adding `m.added_files_count or 0` etc.; `table_observation_from_gateway` builds `ManifestStats` and `PartitionStats` with the new keys.

- [ ] **Step 4: Run them and watch them pass**, then the whole backend suite: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest -q`

- [ ] **Step 5: Commit** (`task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend` first) `feat(table-maintenance): observe record, deletion vector and manifest entry counts (KCL-96)`

### Task 2: `TableMetrics` and `measure_table`

**Files:**
- Create: `TM/application/domain/model/table/table_metrics.py` (export from `TM/application/domain/model/table/__init__.py`), `TM/application/domain/service/table/measure_table.py` (export from its `__init__.py`)
- Test: `tests/context/table_maintenance/application/domain/model/table/test_table_metrics.py`, `tests/context/table_maintenance/application/domain/service/table/test_measure_table.py`

**Interfaces:**
- Consumes: Task 1's fields; `compute_reducible_files` (`TM/application/domain/service/table/`), `resolve_target_file_size` (exported from `TM/application/domain/service/shared`). `measure_table` takes no policy: it never reads `MaintenancePolicyContent`.
- Produces: `class TableMetrics(ValueObject)` with `table_id: TableId`, `observed_at: datetime` (aware), and `int >= 0` fields `data_files`, `position_delete_files`, `equality_delete_files`, `deletion_vectors`, `data_size_bytes`, `data_records`, `position_delete_records`, `equality_delete_records`, `reducible_files`, `manifests`, `manifests_size_bytes`, `manifest_added_entries`, `manifest_existing_entries`, `manifest_deleted_entries`, `snapshots`. Constant `TABLE_METRIC_COUNT_FIELDS: tuple[str, ...]` (those 15 names, in that order) in the same module. `measure_table(table_id: TableId, observation: TableObservation, observed_at: datetime) -> TableMetrics`.

- [ ] **Step 1: Write the failing tests**

```python
def test_measure_sums_every_partition():
    observation = observation_with(partitions=(
        stats(data=3, pos=2, eq=1, dv=1, size=300, data_rec=30, pos_rec=8, eq_rec=4),
        stats(data=2, pos=0, eq=0, dv=0, size=200, data_rec=20, pos_rec=0, eq_rec=0),
    ), manifests=(manifest(100, added=3, existing=1, deleted=0), manifest(50, added=2, existing=0, deleted=1)),
       snapshot_count=4)
    m = measure_table(TableId("t1"), observation, NOW)
    assert (m.data_files, m.position_delete_files, m.equality_delete_files, m.deletion_vectors) == (5, 1, 1, 1)
    assert (m.data_size_bytes, m.data_records, m.position_delete_records, m.equality_delete_records) == (500, 50, 8, 4)
    assert (m.manifests, m.manifests_size_bytes) == (2, 150)
    assert (m.manifest_added_entries, m.manifest_existing_entries, m.manifest_deleted_entries) == (5, 1, 1)
    assert m.snapshots == 4 and m.observed_at == NOW

def test_reducible_files_use_the_tables_target_size(): ...
    # properties {"write.target-file-size-bytes": "100"}, one partition of 4 data files, 250 bytes → 4 - 3 = 1

def test_table_without_snapshot_measures_zero(): ...  # no partitions, manifests or snapshots → every count 0
def test_negative_count_is_refused(): ...             # TableMetrics(..., data_files=-1) → InvariantViolation
def test_naive_observed_at_is_refused(): ...          # InvariantViolation
```

- [ ] **Step 2: Run them and watch them fail:** `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/domain -k "measure or table_metrics" -v` → FAIL, import error.
- [ ] **Step 3: Implement.** `position_delete_files` = sum of `position_delete_file_count − deletion_vector_count`.
- [ ] **Step 4: Run them and watch them pass**
- [ ] **Step 5: Commit** `feat(table-maintenance): measure a table's metrics from its observation (KCL-96)`

### Task 3: `TableMetricsStore` and its SQL store

**Files:**
- Create: `TM/application/port/outbound/table/table_metrics_store.py` (export from `TM/application/port/outbound/table/__init__.py`), `TM/adapter/outbound/table/sql/table_metrics_table.py`, `table_metrics_row_mapper.py`, `table_metrics_sql_store.py` (export `TableMetricsSqlStore` and `table_metrics_table` from `TM/adapter/outbound/table/sql/__init__.py`: `create_schema` imports that package from `AGGREGATE_SQL_PACKAGES`, which is what registers the table on `metadata`), `tests/context/table_maintenance/fakes/in_memory_table_metrics_store.py`
- Test: `tests/context/table_maintenance/adapter/outbound/table/test_table_metrics_sql_store.py` (beside `test_tables_sql_repo.py`; there is no `sql/` test folder), `tests/context/table_maintenance/adapter/outbound/shared/sql/test_create_schema.py` (the `table_metrics` table exists)

**Interfaces:**
- Consumes: `TableMetrics`, `TableId` (Task 2).
- Produces: `class TableMetricsStore(Store)` with abstract `save(metrics: TableMetrics) -> None` (insert, or replace only when `metrics.observed_at` is later than the stored one), `get(table_id: TableId) -> TableMetrics | None`, `list_all() -> list[TableMetrics]` (by table uuid), `delete(table_id: TableId) -> None` (no error when absent). SQL table `table_metrics`: `table_uuid` String primary key, `observed_at` UTC datetime (`UtcDateTime` from `TM/adapter/outbound/shared/sql`, as `tables_table.py` uses it), one `BigInteger` not-null column per count field. `InMemoryTableMetricsStore` keeps the same forward-only rule.

- [ ] **Step 1: Write the failing tests** (run each against the SQL store on SQLite and the in-memory fake, as the other repo tests do)

```python
def test_save_then_get_round_trips(store): ...
def test_newer_metrics_replace_older(store): ...      # save t1, save t2 > t1 → get is t2's values
def test_older_metrics_never_replace_newer(store): ...  # save t2, save t1 → still t2's
def test_two_first_saves_race_to_the_newer(engine): ... # IntegrityError path: the second insert retries as the update
def test_delete_removes_the_row_and_tolerates_absence(store): ...
def test_list_all_orders_by_table_uuid(store): ...
```

- [ ] **Step 2: Run and watch them fail:** `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/adapter/outbound/table/test_table_metrics_sql_store.py tests/context/table_maintenance/adapter/outbound/shared/sql/test_create_schema.py -v`
- [ ] **Step 3: Implement** `save` as `CatalogDiscoveriesSqlRepo.save` (`TM/adapter/outbound/catalog_discovery/sql/catalog_discoveries_sql_repo.py`) does: forward-only update, else insert when no row, retry once on `IntegrityError`.
- [ ] **Step 4: Run and watch them pass**; the architecture suite too: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/architecture -q`
- [ ] **Step 5: Commit** `feat(table-maintenance): keep each table's newest metrics in SQL (KCL-96)`

### Task 4: The reconcile saves the metrics and drops them on a skip

**Files:**
- Modify: `TM/application/service/table/plan_table_maintenance.py` (constructor `(tables_repo, catalog_gateway, resolve_applicable_policy, *, metrics_store: TableMetricsStore, cooldowns=DEFAULT_OPERATION_COOLDOWNS)`; docstring of `execute` gains one sentence: a plan that observes the table saves its metrics, a skip forgets them), `bootstrap/container/repositories.py` (`table_metrics: TableMetricsStore`), `bootstrap/container/build_repositories.py`, `bootstrap/container/build_use_cases.py` (`PlanTableMaintenanceService(tables, catalog, resolve_applicable_policy, metrics_store=repos.table_metrics, cooldowns=cooldowns)`), `tests/context/table_maintenance/fakes/plan_service_on_fakes.py` (optional `metrics_store`, see Global Constraints); only `build_repositories` builds `Repositories` (no test does)
- Test: `tests/context/table_maintenance/application/service/table/test_plan_table_maintenance_service.py` (a `metrics_store` fixture beside `tables_repo` / `catalog`; the `planner` fixture passes it; `test_plan_uses_the_injected_cooldowns` passes one to both of its services), `tests/bootstrap/container/test_build_connected_use_cases.py`

**Interfaces:**
- Consumes: Tasks 2 and 3.
- Produces: every plan that observes a managed table calls `self._metrics_store.save(measure_table(table.id, observation, request.now))` right after `self._record_last_commit(table, observation.last_committed_at)` (inside `with translate_domain_errors():`), manual or scheduled, dry run or not; each of the three skip returns of `execute` (`_skip_unknown_table()`, `_skip(reason, …)` for `dropped` / `unmanaged`, `_skip("not_found", …)`) first calls `self._forget_metrics(request.table_uuid)`, which runs `self._metrics_store.delete(TableId(table_uuid))`.

- [ ] **Step 1: Failing tests:** `test_scheduled_plan_saves_the_tables_metrics` (store holds `data_files` from the fake observation, `observed_at == request.now`); `test_manual_plan_saves_metrics_too`; `test_dry_run_plan_saves_metrics_too` (a policy with `dry_run: true`, via the file's `_use_policy`); `test_plan_of_a_policy_without_compaction_still_saves_reducible_files` (`_use_policy` with `policy_with_only_operation(MaintenanceOperation.EXPIRE_SNAPSHOTS)`); `test_unmanaged_table_loses_its_metrics`; `test_dropped_table_loses_its_metrics`; `test_table_gone_from_the_catalog_loses_its_metrics`; `test_catalog_table_with_another_uuid_loses_its_metrics`; `test_unknown_table_loses_its_metrics`; the container test asserts the built plan service holds a `TableMetricsSqlStore`.
- [ ] **Step 2: Run and watch them fail:** `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/service/table/test_plan_table_maintenance_service.py -k metrics -v`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run and watch them pass**, then the whole suite including `tests/architecture/test_temporal_workflow_determinism.py`
- [ ] **Step 5: Commit** `feat(table-maintenance): save a table's metrics on every reconcile (KCL-96)`

### Task 5: The API exports the metrics in the Prometheus text format

**Files:**
- Create: `TM/application/port/inbound/table/list_table_metrics/{__init__,input,output,use_case}.py`, `TM/application/service/table/list_table_metrics.py`, `TM/adapter/inbound/web/table/table_metrics_exposition.py`, `TM/adapter/inbound/web/table/table_metrics_router.py`
- Modify: `TM/adapter/inbound/web/table/__init__.py` (export `table_metrics_router`), `TM/adapter/inbound/web/register_routes.py` (add `table_metrics_router` to the router tuple, as `platform_settings_router` is), `TM/adapter/inbound/web/shared/web_use_cases.py`, `bootstrap/container/use_cases.py`, `build_use_cases.py`, `build_web_use_cases.py` (`tests/context/table_maintenance/adapter/inbound/web/web_test_support.build_client` derives its stubs from `WebUseCases`, so it needs no change)
- Test: `tests/context/table_maintenance/application/service/table/test_list_table_metrics.py`, `tests/context/table_maintenance/adapter/inbound/web/table/test_table_metrics_exposition.py`, `test_table_metrics_route.py`

**Interfaces:**
- Consumes: `TableMetricsStore.list_all`, `TablesRepo.list_by_statuses`.
- Produces: `ListTableMetricsUseCaseInput()` (no fields), `ListTableMetricsUseCaseOutput(tables: tuple[Table, ...])` with nested `Table(table_uuid: str, catalog: str, namespace: str, table: str, observed_at: datetime, counts: dict[str, int])` (`counts` keyed by `TABLE_METRIC_COUNT_FIELDS`); only rows whose table is managed, names from the current `Table`, ordered by uuid. `render_table_metrics_exposition(output: ListTableMetricsUseCaseOutput) -> str`: per family `# HELP` and `# TYPE <name> gauge`, then one line per table; families in the order of Global Constraints; label values escaped (`\` → `\\`, `"` → `\"`, newline → `\n`); integers without a decimal point; `observed_timestamp_seconds` as seconds with up to 3 decimals; ends with a newline; no families' samples (only `# HELP`/`# TYPE`) when nothing is managed. Route `GET /v1/table-metrics`, shaped like `platform_settings_router` (`TM/adapter/inbound/web/table_maintenance_run/platform_settings_router.py`): `table_metrics_router = APIRouter(tags=["table-metrics"])` with `@table_metrics_router.get("/table-metrics", include_in_schema=False)`, `PlainTextResponse` with media type `text/plain; version=0.0.4; charset=utf-8`.

- [ ] **Step 1: Write the failing tests**

```python
def test_only_managed_tables_are_listed(): ...  # rows for a managed and an unmanaged table → only the managed one

def test_exposition_of_one_table():
    text = render_table_metrics_exposition(output_with_one_table(uuid="u1", catalog="iceberg",
        namespace="retail", table="orders", data_files=12, deletion_vectors=1, manifest_added_entries=4))
    assert '# TYPE iceberg_table_files gauge' in text
    assert 'iceberg_table_info{table_uuid="u1",catalog="iceberg",namespace="retail",table="orders"} 1\n' in text
    assert 'iceberg_table_files{table_uuid="u1",content="data"} 12\n' in text
    assert 'iceberg_table_files{table_uuid="u1",content="deletion_vector"} 1\n' in text
    assert 'iceberg_table_manifest_entries{table_uuid="u1",status="added"} 4\n' in text
    assert text.endswith("\n")

def test_label_values_are_escaped(): ...  # table 'a"b\\c\nd' → table="a\"b\\\\c\\nd"
def test_seventeen_samples_per_table(): ...  # count of non-comment lines for one table == 17
def test_route_serves_text_plain(client): ...  # 200, content-type starts with "text/plain; version=0.0.4"
def test_route_is_not_in_openapi(client): ...  # "/v1/table-metrics" not in client.get("/openapi.json").json()["paths"]
```

- [ ] **Step 2: Run and watch them fail:** `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance -k "table_metrics or exposition" -v`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend` (the contract test confirms `openapi.json` is unchanged)
- [ ] **Step 5: Commit** `feat(table-maintenance): export table metrics for Prometheus (KCL-96)`

### Task 6: Current metrics for the cards, and the unused health and storage endpoints go

**Files:**
- Create: `TM/application/port/inbound/table/get_table_current_metrics/{__init__,input,output,use_case}.py`, `TM/application/service/table/get_table_current_metrics.py`
- Modify: `TM/adapter/inbound/web/table/router.py`, `dto.py`, `__init__.py` (drops the three health / storage DTOs from its exports), `web_use_cases.py`, the bootstrap use-case wiring (`bootstrap/container/use_cases.py`, `build_use_cases.py`, `build_web_use_cases.py`), the exports of `TM/application/port/inbound/table/__init__.py`, `TM/application/service/table/__init__.py`, `TM/application/port/outbound/table/__init__.py` and `TM/application/port/outbound/table/read_table_metadata/__init__.py`, `tests/bootstrap/container/test_build_use_cases.py` and `test_build_connected_use_cases.py` (their health / storage assertions), `openapi.json` and the console's generated client (`task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`)
- Delete: `TM/application/port/inbound/table/get_table_health/`, `get_table_storage/`, `TM/application/service/table/get_table_health.py`, `get_table_storage.py`, `TM/adapter/outbound/table/pyiceberg/storage_measure_mapper.py`, `TM/application/port/outbound/table/read_table_metadata/table_storage_measure.py`, `ReadTableMetadataGateway.measure_storage` and its PyIceberg implementation, the `table_storage_measure.py` entry of `GATEWAY_EXTRA_FILES` in `tests/architecture/test_outbound_port_structure.py`, `TableHealthApiResponse`, `TableHealthOperationApiResponse`, `TableStorageApiResponse`, the tests `tests/context/table_maintenance/adapter/inbound/web/table/test_table_health_route.py`, `test_table_storage_route.py`, `tests/context/table_maintenance/application/service/table/test_get_table_health.py`, `test_get_table_storage.py`, the `measure_storage` tests in `test_read_table_metadata_pyiceberg_gateway.py`, and `measure_storage` in `tests/context/table_maintenance/fakes/fake_read_table_metadata_gateway.py`. `tests/context/table_maintenance/adapter/inbound/web/test_health_and_errors.py` keeps `test_unknown_catalog_maps_to_404`, re-pointed from `get_table_health` / `GET /v1/tables/u-1/health` to `list_table_commits=StubUseCase(error=error)` / `GET /v1/tables/u-1/commits` (same 404 and detail)
- Test: `tests/context/table_maintenance/application/service/table/test_get_table_current_metrics.py`, `tests/context/table_maintenance/adapter/inbound/web/table/test_table_metric_routes.py`, `tests/context/table_maintenance/adapter/inbound/web/table/test_table_health_and_storage_routes_are_gone.py` (new, like `test_table_metadata_route_is_gone.py`)

**Interfaces:**
- Consumes: `TableMetricsStore.get`, `TablesRepo.get`.
- Produces: `GetTableCurrentMetricsUseCaseInput(uuid: str)`, `GetTableCurrentMetricsUseCaseOutput(observed_at: datetime | None, counts: dict[str, int] | None)` (`None` for a table that is not managed or has no row; `NotFoundError` for an unknown table). Route `GET /v1/tables/{table_uuid}/metrics/current` named `get_table_current_metrics`, response `TableCurrentMetricsApiResponse(observed_at: datetime | None, metrics: TableMetricValuesApiResponse | None)`, where `TableMetricValuesApiResponse` has the 15 count fields as `int`.

- [ ] **Step 1: Failing tests:** service: a managed table with a row → its counts; with no row → both `None`; an unmanaged table with a stale row → both `None`; unknown → `NotFoundError`. Routes: `GET /v1/tables/u1/metrics/current` → 200 with `metrics.data_files`; unknown → 404; `GET /v1/tables/u1/health` and `/storage` → 404 (`test_health_and_storage_routes_are_gone`).
- [ ] **Step 2: Run and watch them fail:** `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance -k "current_metrics or routes_are_gone" -v`
- [ ] **Step 3: Implement**, delete the listed files, regenerate the client. The console's `TablePage.test.tsx` stubs `GET …/health` and `…/storage`; leave them (Task 9 rewrites that test), they answer requests nobody sends.
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`
- [ ] **Step 5: Commit** `feat(table-maintenance): serve a table's current metrics and drop the health and storage endpoints (KCL-96)`

### Task 7: Trends from Prometheus through the backend

**Files:**
- Create: `TM/application/domain/model/table/metric_time_range.py`, `TM/application/domain/service/table/derive_metric_trend_values.py`, `TM/application/port/outbound/table/read_table_metric_history/{__init__,gateway,input,output,metric_history_unavailable_error}.py`, `TM/adapter/outbound/table/prometheus/{__init__,read_table_metric_history_prometheus_gateway,promql_string}.py`, `TM/application/port/inbound/table/get_table_metric_trends/{__init__,input,output,use_case}.py`, `TM/application/service/table/get_table_metric_trends.py`, `bootstrap/configs/metrics_settings.py`
- Modify: `tests/architecture/test_outbound_port_structure.py` (`GATEWAY_EXTRA_FILES` gains `metric_history_unavailable_error.py`), `TM/adapter/inbound/web/error_handlers.py` (`MetricHistoryUnavailableError` → 502 in its exception-to-status map, beside `CatalogNotFoundError` → 404), `router.py`, `dto.py`, `bootstrap/configs/app_settings.py` (`metrics: MetricsSettings`), `bootstrap/container/gateways.py`, `build_gateways.py`, the use-case wiring, `openapi.json` + client
- Test: `tests/context/table_maintenance/application/domain/model/table/test_metric_time_range.py`, `tests/context/table_maintenance/application/domain/service/table/test_derive_metric_trend_values.py`, `tests/context/table_maintenance/adapter/outbound/table/prometheus/test_read_table_metric_history_prometheus_gateway.py`, `test_promql_string.py`, `tests/context/table_maintenance/application/service/table/test_get_table_metric_trends.py`, `test_table_metric_routes.py` (Task 6's file), `tests/bootstrap/configs/test_app_settings.py` (defaults and `GLAC_METRICS__*` env). The two metrics settings are wiring, not platform settings: `test_build_platform_settings.py`'s whitelist stays unchanged

**Interfaces:**
- Produces:
  - `class MetricTimeRange(StrEnum)`: `ONE_HOUR = "1h"`, `THREE_HOURS = "3h"`, `SIX_HOURS = "6h"`; properties `duration: timedelta`, `step: timedelta` (30 s, 90 s, 180 s); `default()` → `SIX_HOURS`.
  - `derive_metric_trend_values(values: Mapping[str, float | None]) -> dict[str, float | None]`: returns the input plus `manifest_average_size_bytes` and `manifest_average_entries`.
  - `ReadTableMetricHistoryGatewayInput(table_uuid: str, start_seconds: float, end_seconds: float, step_seconds: int)`; `ReadTableMetricHistoryGatewayOutput(timestamps: list[float], series: dict[str, list[float | None]])`, keys the 15 count field names, each list aligned with `timestamps` (`start`…`end` by step), a missing key meaning no data; `ReadTableMetricHistoryGateway.read(input) -> ReadTableMetricHistoryGatewayOutput`; `MetricHistoryUnavailableError(Exception)` with the reason.
  - Adapter `ReadTableMetricHistoryPrometheusGateway(base_url: str, client: httpx.Client)`: one `GET {base_url}/api/v1/query_range` with the fixed selector; maps `(__name__, content|status)` to the count field name (`iceberg_table_files` + `content="data"` → `data_files`, `deletion_vector` → `deletion_vectors`, `iceberg_table_manifest_entries` + `status="added"` → `manifest_added_entries`, …); ignores `info` and `observed_timestamp_seconds`; takes the max when two series map to one key at a timestamp; `"NaN"` and infinities → `None`; transport error, non-2xx or `"status": "error"` → `MetricHistoryUnavailableError` naming Prometheus's `error` text or the HTTP status.
  - `promql_string(value: str) -> str` returns the double-quoted, escaped literal.
  - `GetTableMetricTrendsUseCaseInput(uuid: str, time_range: str, now: datetime)`; `GetTableMetricTrendsUseCaseOutput(time_range: str, step_seconds: int, start: datetime, end: datetime, points: tuple[Point, ...])`, nested `Point(at: datetime, values: dict[str, float | None])` with every trend key present (15 counts + 2 averages). Unknown table → `NotFoundError`; unknown range → `ValidationError`.
  - Route `GET /v1/tables/{table_uuid}/metrics` named `get_table_metric_trends`, query `range` (`Literal["1h", "3h", "6h"]`, default `"6h"`), response `TableMetricTrendsApiResponse(time_range: str, step_seconds: int, start: datetime, end: datetime, points: list[TableMetricTrendPointApiResponse])`, point `at: datetime`, `values: dict[str, float | None]`.
  - `MetricsSettings(prometheus_url: str = "http://table-metrics-prometheus.table-metrics.svc.cluster.local:9090", query_timeout_seconds: float = 10.0)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_every_range_has_120_steps():
    for r in MetricTimeRange:
        assert r.duration / r.step == 120

def test_averages_divide_by_manifests():
    got = derive_metric_trend_values({"manifests": 4, "manifests_size_bytes": 400, "manifest_added_entries": 6,
                                      "manifest_existing_entries": 2, "manifest_deleted_entries": 0})
    assert got["manifest_average_size_bytes"] == 100 and got["manifest_average_entries"] == 2

def test_averages_are_null_without_manifests(): ...  # manifests 0 or None → both None

def test_promql_string_escapes():
    assert promql_string('a"b\\c\nd') == '"a\\"b\\\\c\\nd"'

def test_gateway_sends_the_fixed_query(): ...
    # httpx.MockTransport records the request: path /api/v1/query_range,
    # query == '{__name__=~"iceberg_table_.+", table_uuid="u1"}', start/end/step as given
def test_gateway_aligns_series_and_fills_gaps(): ...   # values at t0 and t2 only → [v0, None, v2]
def test_gateway_maps_content_and_status_labels(): ... # files{content="equality_delete"} → equality_delete_files
def test_gateway_turns_nan_into_none(): ...
def test_gateway_error_status_is_unavailable(): ...    # {"status":"error","error":"bad"} → MetricHistoryUnavailableError("…bad…")
def test_gateway_connection_error_is_unavailable(): ...

def test_trends_window_ends_on_a_step(): ...  # now 12:00:47, 1h → end 12:00:30, start 11:00:30, 121 points
def test_trends_of_unknown_table_is_not_found(): ...
def test_route_rejects_an_unknown_range(client): ...  # ?range=7d → 422
def test_route_answers_502_when_prometheus_is_down(client): ...  # detail names the reason
```

- [ ] **Step 2: Run and watch them fail:** `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance tests/bootstrap -k "metric_time_range or trend or promql or metric_history or metrics_settings" -v`
- [ ] **Step 3: Implement**, then `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`. Build the gateway's `httpx.Client` in `build_gateways(settings, *, client, bridge, k8s_api, k8s_core_api, catalog_factory)` with `timeout=settings.metrics.query_timeout_seconds`, and add `read_table_metric_history: ReadTableMetricHistoryGateway` to the `Gateways` bundle (and to the `Gateways(...)` that `tests/bootstrap/container/container_support.py` builds); nothing connects at build time.
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`
- [ ] **Step 5: Commit** `feat(table-maintenance): read a table's metric trends from Prometheus (KCL-96)`

### Task 8: A small Prometheus scrapes the exporter

**Files:**
- Create: `platform/26-table-metrics-prometheus/{bootstrap.sh,validate.sh,README.md,prometheus-configmap.yaml,prometheus-pvc.yaml,prometheus-deployment.yaml,prometheus-service.yaml}`
- Modify: `tasks/apps.yml` (`bootstrap-by-scripts` `status` (`TIMEOUT=10s bash platform/26-table-metrics-prometheus/validate.sh`) and `cmds` (`bootstrap.sh` then `validate.sh`) right after the wave-25 lines, the `validate` chain, and a `validate-table-metrics-prometheus` task like `validate-lakehouse-control-plane`), `platform/25-lakehouse-control-plane/chart/values.yaml` (`metrics.prometheusUrl`), `chart/templates/configmap.yaml` (`GLAC_METRICS__PROMETHEUS_URL`), `platform/25-lakehouse-control-plane/README.md` (the three metrics endpoints)

**Interfaces:**
- Consumes: Task 5's `/v1/table-metrics`, Task 7's env var name.

- [ ] **Step 1: Write the failing check.** `validate.sh` follows `platform/23-kafka-ui/validate.sh`: sources `scripts/utils/log.sh` and `scripts/utils/namespace.sh`, requires `KUBE_CONTEXT` (`: "${KUBE_CONTEXT:?KUBE_CONTEXT is required}"`), `TIMEOUT="${TIMEOUT:-300s}"`, `log::on_success` / `log::on_failure`, then: `namespace::assert_ambient table-metrics`; `kubectl rollout status deployment/table-metrics-prometheus --namespace table-metrics --timeout "${TIMEOUT}" --context "${KUBE_CONTEXT}"`; through the API server proxy (`kubectl get --raw "/api/v1/namespaces/table-metrics/services/http:table-metrics-prometheus:9090/proxy/api/v1/query?query=…" --context "${KUBE_CONTEXT}"`, read with `yq -p json`) it waits up to 120 s for `up{job="table-maintenance-api"}` to be `1`, and checks `/api/v1/status/flags` reports `storage.tsdb.retention.time` `6h`; last, `mesh::assert_hbone table-metrics`.
- [ ] **Step 2: Run** `KUBE_CONTEXT=retail-lakehouse bash platform/26-table-metrics-prometheus/validate.sh` and expect it to fail (nothing deployed).
- [ ] **Step 3: Implement** the manifests with the Global Constraints values (security context `runAsNonRoot`, `runAsUser` and `fsGroup` 65534; readiness `/-/ready`, liveness `/-/healthy`); `bootstrap.sh` runs `namespace::apply_ambient table-metrics` and `kubectl apply` for each file. No comments in the YAML.
- [ ] **Step 4: Run** `uv run pre-commit run k8s-labels --all-files` and `uv run pre-commit run shared --all-files`; both pass. `helm template platform/25-lakehouse-control-plane/chart | grep GLAC_METRICS__PROMETHEUS_URL` prints one line.
- [ ] **Step 5: Commit** `feat(platform): add a small Prometheus for table metrics (KCL-96)`

### Task 9: The Overview shows the metric cards and trends

**Files:**
- Create: `src/data-platform/frontend/src/lib/metricTrendRows.ts` + `.test.ts`, `src/data-platform/frontend/src/components/tabs/useMetricRange.ts`, `src/data-platform/frontend/src/components/TableMetricsDashboard.tsx` + `.test.tsx` + `.stories.tsx`
- Modify: `src/data-platform/frontend/src/components/tabs/OverviewTab.tsx`, `src/data-platform/frontend/src/stories/storyData.ts` (`ORDERS_CURRENT_METRICS`, `ORDERS_METRIC_TRENDS`, typed with the generated models, as `COMMITS` and `RECONCILIATIONS` are), `src/stories/lakehouseHandlers.ts` (the two generated mock handlers from `@/api/generated/tables/tables.msw`, in the list `lakehouseHandlers()` returns), `src/data-platform/frontend/src/pages/TablePage.test.tsx` (`stubTable` drops the `GET /v1/tables/uuid-orders/health` and `/storage` stubs and gains `GET /v1/tables/uuid-orders/metrics/current` and `GET /v1/tables/uuid-orders/metrics*`; the test "overview holds only the Table panel: no health, storage, freshness, commits or runs" becomes "overview shows the metrics dashboard above the Table panel, and no commits or runs", still asserting no request to `commits*` or `table-maintenance-runs`), `src/pages/TablePage.stories.tsx` (the `Overview` story also finds the six cards; new `OverviewTrendsUnavailable` (`apiError` on `GET /v1/tables/:tableUuid/metrics`, 502), `OverviewNotReconciledYet` (`/metrics/current` answers `observed_at: null`, `metrics: null`) and `OverviewPhone` (`globals: PHONE`, `expectNoHorizontalPageScroll`)). `TablePage.mobile.test.tsx` needs nothing: its table is not managed, so no dashboard renders

**Interfaces:**
- Consumes: the generated `useGetTableCurrentMetrics(tableUuid)`, `useGetTableMetricTrends(tableUuid, { range })`, `TableCurrentMetricsApiResponse`, `TableMetricTrendsApiResponse`, `GetTableMetricTrendsRange`.
- Produces: `metricTrendRows(trends: TableMetricTrendsApiResponse) -> Array<{ time: string } & Record<string, number | null>>`; `metricDelta(trends, key, current: number, rangeLabel: string) -> MetricCardDelta | undefined` (first non-null value in the window against `current`: `"+12 in 6h"`, `"−6 in 6h"` with U+2212, `"No change in 6h"`; direction `up` / `down` / `flat`; tone always `"neutral"`; `undefined` when the window has no value); `useMetricRange() -> { range: "1h" | "3h" | "6h"; setRange(next) }` (url `?range=`, invalid or missing → `6h`, `6h` removes the parameter, `replace` navigation); `TableMetricsDashboard({ tableUuid }: { tableUuid: string })`.

- [ ] **Step 1: Write the failing tests and stories**
  - `metricTrendRows` keeps every point in order with `null` gaps; `metricDelta` gives `"+12 in 6h"` / `up`, `"−6 in 1h"` / `down`, `"No change in 3h"` / `flat`, and `undefined` for an all-null series.
  - `TableMetricsDashboard`: the six cards in order with formatted values (`formatCount`, `formatBytes`); not reconciled yet → every card `—` and the note "Metrics appear after the table's next reconciliation."; trend request 502 → every chart shows `Trends unavailable: <detail>` in its error state while the cards keep their values; choosing `1h` requests `range=1h` and puts `?range=1h` in the url; six sections (`getAllByRole("region")`).
  - Story play functions (keyboard): Tab reaches the range picker, arrow keys move between `1h` / `3h` / `6h` and Space or Enter selects; Tab reaches each chart and the arrow keys move its tooltip; phone width has no horizontal page scroll (`expectNoHorizontalPageScroll`); axe passes.
- [ ] **Step 2: Run and watch them fail:** `npm --prefix src/data-platform/frontend test -- --run metricTrendRows TableMetricsDashboard TablePage`
- [ ] **Step 3: Implement** with design-system parts only: `Panel` per section (title as in Global Constraints), `MetricCard` with `trend` from the series (its `trend` is `readonly number[]`, so the `null` points are left out; `delta` is a `MetricCardDelta`), `LineChart` / `AreaChart` with `index="time"` (their `error` prop carries the unavailable text), `TimeRangePicker` with options `{ value, label, description: "Last N hour(s)" }` (`TimeRangeOption.description` is a string). `OverviewTab` renders `<TableMetricsDashboard tableUuid={managed.uuid} />` when `maintenance.kind === "managed"` (its existing `managed` const), first in its grid, and drops the Table panel's Rows, Data files and Size `Fact`s together with the `table.summary` destructuring and the `formatBytes` / `formatCount` imports they used.
- [ ] **Step 4: Run and watch them pass**; `npm --prefix src/data-platform/frontend run test:stories`; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`
- [ ] **Step 5: Commit** `feat(console): show a table's metric cards and trends on the Overview (KCL-96)`

### Task 10: Record the decision and update the docs

**Files:**
- Create: `docs/adr/0013-table-metrics-in-the-database-and-prometheus.md` (context, the three options from the KCL-69 comment of 2026-11-17 — exporter from the database, remote write, worker memory — the decision, consequences: flat lines between reconciles, cards and charts may differ by one scrape, Prometheus series grow with tables)
- Modify: `CLAUDE.md` (ADR list gains 0013), `src/data-platform/backend/CLAUDE.md` (a paragraph after the maintenance policy paragraph: the table metrics store, saved by every plan that observes the table and forgotten on every skip, the exporter, the trend gateway, and that the browser never sends PromQL), `src/data-platform/frontend/CLAUDE.md` ("The table page joins two APIs": the Overview's dashboard reads the maintenance API, for a managed table only), `platform/CLAUDE.md` (a wave-26 line under "Deployed waves"; `table-metrics` added to the ambient "Enrolled namespaces" list; the "Observability paused" paragraph says wave 26 is a separate Prometheus for table metrics, not kube-prometheus), `platform/25-lakehouse-control-plane/README.md` if Task 8 did not already list the metrics endpoints, `docs/agents/known-follow-ups.md` (remove the entries on the Overview Table panel's repeated rows and on the unused `ChartContainer` / `recharts`; add: Prometheus memory grows by 17 series per managed table, so 20 000 tables need 1 to 2 GiB and a longer scrape interval or sharding; a rename keeps the series but changes `iceberg_table_info`; the cards and charts read different sources and may differ by one scrape), `docs/agents/project-history.md` (one line)
- [ ] **Step 1:** Write the files; `uv run pre-commit run shared --all-files` passes.
- [ ] **Step 2: Commit** `docs: record table metrics and their trends (KCL-96)`

### Task 11: Verify on a rebuilt cluster (controller)

**Batched (refreshed 2026-11-20):** the controller runs this task in one batch rebuild with KCL-91 (Task 9 of `docs/superpowers/plans/2026-11-20-maintenance-policy-target-state.md`) and KCL-97 (Task 10 of `docs/superpowers/plans/2026-11-20-schema-version-diff.md`), after both plans here are implemented: Step 1 is done once for the three, then each plan's checks run on that cluster. The checks below stay as they are.

- [ ] **Step 1:** `task -d /Users/kcl/Projects/retail-lakehouse offboard KUBE_CONTEXT=retail-lakehouse`, then `task -d /Users/kcl/Projects/retail-lakehouse onboard KUBE_CONTEXT=retail-lakehouse`; `task -d /Users/kcl/Projects/retail-lakehouse apps:validate KUBE_CONTEXT=retail-lakehouse` exits 0, including `26-table-metrics-prometheus`.
- [ ] **Step 2:** Port-forward the gateway (`kubectl port-forward service/platform-gateway-istio 8591:80 --namespace istio-ingress --context retail-lakehouse`); API calls go through `gateway::curl` (Global Constraints, "Cluster access"). If no discovery rule manages `iceberg / inventory / *` yet (KCL-91's batch checks manage only `iceberg / kcl91 / *`), add one with `PUT /api/v1/discovery-rules` (after KCL-71, a discovery policy attached to `iceberg.inventory`); the CDC table `iceberg.inventory.orders` is then managed and its first reconciliation records `{"table_managed": 1}`. Take its uuid from `GET /api/v1/tables`, `POST /api/v1/tables/{uuid}/reconcile`, then `GET /api/v1/table-metrics` lists it with 17 samples and `GET /api/v1/tables/{uuid}/metrics/current` returns its counts; the counts match the table header's rows and data files.
- [ ] **Step 3:** Insert rows through MySQL (the CDC path), wait for the Iceberg sink to commit (up to 10 minutes, see known follow-ups); the default policy's commit window (300 s) then checks the table by itself, or `POST …/reconcile` again: `/metrics/current` moves, and within a minute `GET /api/v1/tables/{uuid}/metrics?range=1h` shows the step in `data_files` and `data_records`.
- [ ] **Step 4:** In the console (`http://localhost:8591/console/`, logged in as `platform-admin`) open the table's Overview: six cards, six sections with data, switching `1h` / `3h` / `6h` changes the url and the charts; run a manual compaction and after its reconcile the data files and reducible files drop on the cards and the charts. Scale `table-metrics-prometheus` to 0 (`kubectl scale deployment/table-metrics-prometheus --replicas 0 --namespace table-metrics --context retail-lakehouse`): the cards still show and the charts say the trends are unavailable; scale it back to 1.
- [ ] **Step 5:** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`; record the results on KCL-96 in a dated comment; push only when the user asks.
