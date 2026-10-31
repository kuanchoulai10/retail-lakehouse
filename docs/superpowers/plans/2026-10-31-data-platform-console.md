# Data Platform Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a table-owner console (table list + tabbed table page with Health, Storage and Freshness) in front of the table-maintenance API, backed by four new read-only endpoints, deployed on minikube under `/console`.

**Architecture:** The backend gains one domain evaluation (`assess_maintenance`) that both the scheduler and the Health endpoint read, three new reads on `ReadTableMetadataGateway`, and four use cases with routes under `/v1/tables/{uuid}/`. The console is a Vite React SPA in `src/console/`, served by nginx, which also proxies `/console/api/` to the API, and is reached through `platform-gateway` with an `HTTPRoute`.

**Tech Stack:** Python 3.14, FastAPI, PyIceberg 0.11.1, SQLAlchemy, pytest (backend); React 18, TypeScript, Vite, React Router, TanStack Query, Vitest, Testing Library (console); nginx, Helm, Gateway API.

**Spec:** `docs/superpowers/specs/2026-10-31-data-platform-console-design.md`

## Global Constraints

- Backend rules in `CLAUDE.md` bind every backend task: aggregate axis, boundary-only imports, ports speak intent (no `iceberg`, `pyiceberg`, `spark`, `kafka` … in `application/` names), one object per file, `from __future__ import annotations`, ABC not Protocol, StrEnum, use-case outputs as application dataclasses, DTO suffixes `UseCaseInput` / `UseCaseOutput` / `UseCaseOutputItem` / `ApiResponse`.
- Backend CHECKS before every commit, from the repo root: `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -q`, `… ty check`, `… ruff check .`, `… ruff format --check .`, `… lint-imports`.
- Console CHECKS before every console commit: `npm --prefix src/console run typecheck`, `npm --prefix src/console run lint`, `npm --prefix src/console test -- --run`, `npm --prefix src/console run build`.
- TDD: failing test first, watch it fail, then code.
- Every existing planner test in `tests/application/domain/service/table/test_plan_scheduled_maintenance.py` keeps passing unchanged.
- Endpoints (exact): `GET /v1/tables/{uuid}/metadata`, `GET /v1/tables/{uuid}/commits?limit=&since=` (`limit` default 100, max 1000; `since` ISO-8601; response carries `truncated`), `GET /v1/tables/{uuid}/health`, `GET /v1/tables/{uuid}/storage`.
- Unknown table → 404. Table in the DB but missing in the catalog → 404 from the four endpoints with detail `table <catalog>.<namespace>.<table> is not in the catalog`.
- Writer rule: summary key starting `kafka.connect.` → `kafka_connect`; `spark.app.id` present → `spark`; else `unknown`.
- Console lives at `/console/`, calls the API at `/console/api/v1/…`; UI copy is English.
- Shell: no `cd`, absolute paths or `--project` / `--prefix` / `git -C`; `uv run`, never bare python. kubectl: verb first, flags last. YAML: no explanatory comments. Never print secret values.
- Commits: conventional, each line ≤100 chars, on `main`, never push. Every commit message ends with a blank line then `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.

## Review Focus

1. A table with no snapshots yet (registered, empty): every endpoint answers 200 with zeros / empty lists, and the page renders "no commits yet" instead of crashing. Tests: Task 2 (`test_describe_empty_table`), Task 3 (`test_metadata_of_empty_table`), Task 9 (`renders an empty table`).
2. A `PAUSED` / `EXCLUDED` table on the Health tab: `scheduled: false` with the reason, lines labelled "would be due when resumed". Test: Task 5 (`test_paused_table_is_not_scheduled_but_assessed`), Task 9 (`shows the not-scheduled banner`).
3. A table whose catalog entry vanished (`not_found`): the four endpoints 404 with the catalog detail and the page still shows the DB fields with a "not in catalog" notice. Tests: Task 3 (`test_metadata_404_when_not_in_catalog`), Task 8 (`shows not-in-catalog notice`).
4. Commit summaries with missing or non-numeric counters (older writers, `delete` operations): added / removed figures become `null`, never 500. Test: Task 4 (`test_commit_with_partial_summary`).
5. A deep link or reload on `/console/tables/<uuid>/commits` must serve the SPA, not an nginx 404. Test: Task 11 (`validate.sh` curls a deep link).

---

### Task 1: One maintenance evaluation for scheduler and Health

**Files:**
- Create: `application/domain/model/shared/operation_verdict.py`, `size_source.py`, `operation_assessment.py`, `maintenance_assessment.py` (all under `src/table-maintenance/backend/`), re-exported from `application/domain/model/shared/__init__.py`
- Create: `application/domain/service/table/assess_maintenance.py`
- Modify: `application/domain/service/table/plan_scheduled_maintenance.py`, `application/domain/service/table/__init__.py`
- Test: `tests/application/domain/service/table/test_assess_maintenance.py`

**Interfaces:**
- Produces:
  - `OperationVerdict(StrEnum)`: `DUE="due"`, `NOT_DUE="not_due"`, `DISABLED="disabled"`, `COOLDOWN="cooldown"`.
  - `SizeSource(StrEnum)`: `SETTINGS="settings"`, `TABLE_PROPERTY="table_property"`, `DEFAULT="default"`.
  - `OperationAssessment(ValueObject)`: `operation: MaintenanceOperation`, `verdict: OperationVerdict`, `measured: int | None`, `threshold: int | None`, `next_eligible_at: datetime | None`, `qualifying_partitions: int | None`, `size_bytes: int | None`, `size_source: SizeSource | None`, `planned: PlannedOperation | None` (set iff `verdict == DUE`).
  - `MaintenanceAssessment(ValueObject)`: `operations: tuple[OperationAssessment, ...]` in `MaintenanceOperation.ordered()` order; `def plan(self) -> MaintenancePlan` returns the `planned` of the due ones.
  - `assess_maintenance(table: Table, settings: MaintenanceSettings, observation: TableObservation, now: datetime) -> MaintenanceAssessment` — ignores `table.status`; uses `table.operation_state(op)` for cooldown.
  - `plan_scheduled_maintenance` keeps its signature and becomes: not ACTIVE or no settings → `MaintenancePlan()`, else `assess_maintenance(table, table.settings, observation, now).plan()`.

Per operation (spec table): `rewrite_data_files` — `scope=TABLE`: `measured` = summed reducible, `qualifying_partitions=None`; `scope=PARTITION`: `measured` = summed reducible of qualifying partitions, `qualifying_partitions` = their count; `threshold=min_reducible_files`; `size_bytes` = resolved target, `size_source` = SETTINGS if `target_file_size_bytes` set, TABLE_PROPERTY if `write.target-file-size-bytes` is a positive int, else DEFAULT. `rewrite_manifests` — `measured` = small manifests, `threshold=min_small_manifests`, `size_bytes` = byte threshold, source SETTINGS / TABLE_PROPERTY (`commit.manifest.target-size-bytes`) / DEFAULT. `expire_snapshots` — `measured` = count of expirable snapshots, `threshold=1`. `remove_orphan_files` — `measured=None`, `threshold=None`. Disabled → `DISABLED`, all measures `None`, `next_eligible_at=None`. In cooldown → `COOLDOWN`, `next_eligible_at = last_attempt_at + effective_cooldown(min_interval)`, measures still computed.

- [ ] **Step 1: Write the failing tests** in `test_assess_maintenance.py`, reusing the builders of `test_plan_scheduled_maintenance.py` (copy its `table(...)` / observation helpers into the new file):
  - `test_partition_scope_counts_qualifying_partitions` — two partitions with 6 and 2 reducible files, `min_reducible_files=5` → `verdict == DUE`, `measured == 6`, `qualifying_partitions == 1`, `threshold == 5`.
  - `test_table_scope_sums_every_partition` — same partitions, `scope=TABLE` → `measured == 8`, `qualifying_partitions is None`, DUE.
  - `test_target_size_source` — parametrized: settings `target_file_size_bytes=1024` → `(1024, SETTINGS)`; property `write.target-file-size-bytes=2048` → `(2048, TABLE_PROPERTY)`; neither → `(536870912, DEFAULT)`.
  - `test_expire_snapshots_counts_expirable` — 14 snapshots older than cutoff, `retain_last=10`, none current among the old → `measured == 4`, DUE; with `retain_last=20` → `measured == 0`, `NOT_DUE`.
  - `test_cooldown_reports_next_eligible_time` — `last_attempt_at = now - 30min`, `min_interval=1h`, no failures → `COOLDOWN`, `next_eligible_at == now + 30min`, `planned is None`.
  - `test_disabled_operation_has_no_measures` — `remove_orphan_files` disabled → `DISABLED`, `measured is None`, `next_eligible_at is None`.
  - `test_assessment_ignores_status` — a `PAUSED` table with a due compaction → assessment DUE while `plan_scheduled_maintenance(...)` is empty.
  - `test_plan_equals_due_operations` — for one mixed fixture, `assess_maintenance(...).plan() == plan_scheduled_maintenance(...)` on an ACTIVE table.
- [ ] **Step 2: Run** `uv run --project src/table-maintenance/backend --directory src/table-maintenance/backend pytest -q tests/application/domain/service/table/test_assess_maintenance.py` — Expected: FAIL (`ImportError: assess_maintenance`).
- [ ] **Step 3: Implement** the four value objects and `assess_maintenance`, moving the per-operation logic out of `plan_scheduled_maintenance.py` (keep `DEFAULT_SMALL_MANIFEST_BYTES` / `MANIFEST_TARGET_SIZE_PROPERTY` exported where they are, or move them with a re-export so existing imports hold). Reduce `plan_scheduled_maintenance` to the status guard plus `.plan()`.
- [ ] **Step 4: Run** the new test file and `tests/application/domain/service/table/test_plan_scheduled_maintenance.py` — Expected: all PASS, the old file unchanged. Then run the full CHECKS.
- [ ] **Step 5: Commit** `refactor(table-maintenance): derive the scheduled plan from one maintenance assessment`

### Task 2: Three new reads on the table metadata gateway

**Files:**
- Create under `application/port/outbound/table/read_table_metadata/`: `table_description.py` (`TableDescription`), `table_commit_page.py` (`TableCommitPage`), `table_storage_measure.py` (`TableStorageMeasure`); re-export from its `__init__.py`
- Modify: `application/port/outbound/table/read_table_metadata/gateway.py`, `adapter/outbound/table/pyiceberg/read_table_metadata_pyiceberg_gateway.py`
- Create: `adapter/outbound/table/pyiceberg/description_mapper.py`, `commit_page_mapper.py`, `storage_measure_mapper.py`
- Test: `tests/adapter/outbound/table/pyiceberg/test_read_table_metadata_pyiceberg_gateway.py` (extend; it already builds a `SqlCatalog` in `tmp_path`)

**Interfaces:**
- Produces (primitive-only frozen dataclasses):
  - `TableDescription`: `table_uuid: str`, `format_version: int`, `location: str`, `properties: dict[str, str]`, `schema_fields: list[dict]` (items `{"field_id", "name", "type", "required"}`, current schema), `specs: list[dict]` (same shape as `TableMetadataObservation.specs`), `current_snapshot_id: int | None`, `current_summary: dict[str, str]`, `snapshot_count: int`, `last_committed_at: str | None` (ISO-8601 of the current snapshot).
  - `TableCommitPage`: `commits: list[dict]` (items `{"snapshot_id": int, "parent_id": int | None, "committed_at": str, "operation": str | None, "summary": dict[str, str]}`, newest first), `truncated: bool`.
  - `TableStorageMeasure`: `current_bytes: int`, `current_files: int`, `referenced_bytes: int`, `referenced_files: int` — current = data + delete files of the current snapshot; referenced = distinct file paths over all snapshots (`table.inspect.all_files()`); empty table → all 0.
  - New abstract methods on `ReadTableMetadataGateway`: `describe_table(ref: TableMetadataRef) -> TableDescription | None`, `list_commits(ref: TableMetadataRef, since: str | None, limit: int) -> TableCommitPage | None`, `measure_storage(ref: TableMetadataRef) -> TableStorageMeasure | None`. `None` means the table is not in the catalog. `truncated` is true iff more snapshots at or after `since` exist than `limit`.
  - Every fake/in-memory implementation of the gateway in `tests/` gains the three methods (find them with `grep -rl "ReadTableMetadataGateway)" src/table-maintenance/backend/tests`).

- [ ] **Step 1: Write the failing tests** against the real `SqlCatalog`: `test_describe_partitioned_table` (format version, location, schema field names, spec field `day`, `snapshot_count == 2` after two appends, `current_summary["operation"] == "append"`); `test_describe_empty_table` (`current_snapshot_id is None`, `snapshot_count == 0`, `current_summary == {}`); `test_list_commits_newest_first_with_limit` (three appends, `limit=2` → two commits, newest first, `truncated is True`); `test_list_commits_since` (`since` = the second commit's time → 2 commits, `truncated is False`); `test_measure_storage_counts_files_kept_by_old_snapshots` (append, then overwrite → `referenced_files > current_files`, `referenced_bytes > current_bytes`); `test_reads_return_none_for_missing_table`.
- [ ] **Step 2: Run** that test file — Expected: FAIL (`AttributeError: describe_table`).
- [ ] **Step 3: Implement** the port types, the abstract methods, and the PyIceberg mappers (one function per mapper file; reuse `_load` for `None`).
- [ ] **Step 4: Run** the test file, then full CHECKS (architecture tests cover the new port files) — Expected: PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): read table description, commits and storage from the catalog`

### Task 3: `GET /v1/tables/{uuid}/metadata`

**Files:**
- Create: `application/port/inbound/table/get_table_metadata/{__init__,input,output,use_case}.py`, `application/service/table/get_table_metadata.py`, `application/service/table/load_catalog_table.py`
- Modify: `adapter/inbound/web/table/router.py`, `adapter/inbound/web/table/dto.py`, `bootstrap/container/use_cases.py` + `build_use_cases.py`, the inbound/service `__init__.py` re-exports
- Test: `tests/application/service/table/test_get_table_metadata.py`, `tests/adapter/inbound/web/table/test_table_metadata_route.py`

**Interfaces:**
- Produces:
  - `load_catalog_table(tables_repo: TablesRepo, uuid: str) -> tuple[Table, TableMetadataRef]` — raises `NotFoundError(f"table {uuid} not found")` for an unknown uuid. Tasks 4–6 reuse it.
  - `raise_not_in_catalog(table: Table) -> NoReturn` in `application/service/table/raise_not_in_catalog.py`, raising `NotFoundError(f"table {catalog}.{namespace}.{table} is not in the catalog")`.
  - `GetTableMetadataUseCaseInput(uuid: str)`; `GetTableMetadataUseCaseOutput`: `uuid`, `format_version`, `location`, `properties`, `schema_fields: list[dict]`, `specs: list[dict]`, `current_snapshot_id: int | None`, `snapshot_count: int`, `last_committed_at: datetime | None`, `total_records: int | None`, `total_data_files: int | None`, `total_delete_files: int | None`, `total_files_size_bytes: int | None` (from the current summary keys `total-records`, `total-data-files`, `total-delete-files`, `total-files-size`; missing or non-numeric → `None`).
  - Route returns `TableMetadataApiResponse` with the same fields.
- [ ] **Step 1: Failing tests:** service — `test_metadata_maps_summary_totals` (summary `{"total-records": "1204331", "total-data-files": "15", "total-files-size": "50540544"}` → those ints), `test_metadata_of_empty_table` (no snapshot → totals `None`, `snapshot_count == 0`), `test_metadata_unknown_table_raises_not_found`, `test_metadata_404_when_not_in_catalog` (gateway returns `None` → `NotFoundError` whose message ends `is not in the catalog`); web — `test_get_metadata_returns_200` and `test_get_metadata_404_detail` through the app test client (follow `tests/adapter/inbound/web/web_test_support.py`).
- [ ] **Step 2: Run** them — Expected: FAIL (import errors).
- [ ] **Step 3: Implement** port, service, helpers, DTO, route, wiring.
- [ ] **Step 4: Run** tests then full CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): serve a table's catalog metadata`

### Task 4: `GET /v1/tables/{uuid}/commits`

**Files:**
- Create: `application/domain/model/table/commit_writer.py` (`CommitWriter(StrEnum)`: `KAFKA_CONNECT="kafka_connect"`, `SPARK="spark"`, `UNKNOWN="unknown"`), `application/domain/service/table/commit_writer_of.py`, `application/port/inbound/table/list_table_commits/…`, `application/service/table/list_table_commits.py`
- Modify: router, dto, container, re-exports
- Test: `tests/application/domain/service/table/test_commit_writer_of.py`, `tests/application/service/table/test_list_table_commits.py`, `tests/adapter/inbound/web/table/test_table_commits_route.py`

**Interfaces:**
- Consumes: `load_catalog_table`, `raise_not_in_catalog` (Task 3); `list_commits` (Task 2).
- Produces: `commit_writer_of(summary: dict[str, str]) -> CommitWriter` (spec rule). `ListTableCommitsUseCaseInput(uuid: str, limit: int = 100, since: datetime | None = None)`; output `items: list[ListTableCommitsUseCaseOutputItem]`, `truncated: bool`; item: `snapshot_id: int`, `parent_id: int | None`, `committed_at: datetime`, `operation: str | None`, `writer: str`, `added_records`, `deleted_records`, `added_data_files`, `deleted_data_files`, `added_delete_files`, `removed_delete_files` (all `int | None`, from summary keys `added-records`, `deleted-records`, `added-data-files`, `deleted-data-files`, `added-delete-files`, `removed-delete-files`), `summary: dict[str, str]`. Route: `limit: int = Query(100, ge=1, le=1000)`, `since: datetime | None`; out-of-range `limit` → 422.
- [ ] **Step 1: Failing tests:** `test_writer_kafka_connect` (`{"kafka.connect.commit-id": "x"}`), `test_writer_spark` (`{"spark.app.id": "app-1"}`), `test_writer_unknown`; service `test_commits_map_counters_and_writer`, `test_commit_with_partial_summary` (`{"added-records": "abc"}` → `added_records is None`, no exception), `test_truncated_passes_through`; web `test_commits_limit_over_1000_is_422`, `test_commits_since_is_forwarded`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** tests then full CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): list a table's commits with their writer`

### Task 5: `GET /v1/tables/{uuid}/health`

**Files:**
- Create: `application/port/inbound/table/get_table_health/…`, `application/service/table/get_table_health.py`
- Modify: router, dto, container, re-exports
- Test: `tests/application/service/table/test_get_table_health.py`, `tests/adapter/inbound/web/table/test_table_health_route.py`

**Interfaces:**
- Consumes: `assess_maintenance`, `OperationVerdict`, `SizeSource` (Task 1); `load_catalog_table`, `raise_not_in_catalog` (Task 3); `observe_table` and `table_observation_from_gateway` (existing).
- Produces: `GetTableHealthUseCaseInput(uuid: str)`; output `scheduled: bool`, `not_scheduled_reason: str | None` (`"paused"`, `"excluded"`, `"dropped"`, `"no_settings"`), `operations: list[GetTableHealthUseCaseOutputItem]`, `position_delete_files: int`, `equality_delete_files: int` (summed over `observation.partitions`); item: `operation`, `verdict`, `measured`, `threshold`, `next_eligible_at: datetime | None`, `qualifying_partitions`, `size_bytes`, `size_source: str | None`. `now` comes from the service's injected clock (follow how existing services get `now`). No settings → `scheduled=False`, reason `no_settings`, `operations=[]`.
- [ ] **Step 1: Failing tests:** `test_active_table_reports_each_operation_in_order`, `test_paused_table_is_not_scheduled_but_assessed` (reason `paused`, four items present), `test_table_without_settings_has_no_lines`, `test_delete_file_counts_are_summed`, `test_health_404_when_not_in_catalog`; web `test_get_health_returns_verdict_strings` (`"due"`, `"cooldown"` serialized as strings).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** tests then full CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): report a table's maintenance health from the scheduler's assessment`

### Task 6: `GET /v1/tables/{uuid}/storage`

**Files:**
- Modify: `application/port/outbound/table_maintenance_run/table_maintenance_runs_repo.py` (new method), `adapter/outbound/table_maintenance_run/sql/table_maintenance_runs_sql_repo.py`, every test fake of the repo
- Create: `application/port/inbound/table/get_table_storage/…`, `application/service/table/get_table_storage.py`
- Modify: router, dto, container, re-exports
- Test: `tests/adapter/outbound/table_maintenance_run/test_table_maintenance_runs_sql_repo.py` (extend or create next to the existing repo test), `tests/application/service/table/test_get_table_storage.py`, `tests/adapter/inbound/web/table/test_table_storage_route.py`

**Interfaces:**
- Consumes: `measure_storage` (Task 2); `load_catalog_table` (Task 3).
- Produces: `TableMaintenanceRunsRepo.list_by_table_since(table_uuid: TableId, since: datetime) -> list[TableMaintenanceRun]` (runs with `created_at >= since`, newest first, no limit). `GetTableStorageUseCaseInput(uuid: str)`; output `current_bytes`, `current_files`, `old_snapshot_bytes` (= referenced − current, floored at 0), `old_snapshot_files`, `window_days: int` (30), `reclaimed: dict[str, int]` with keys exactly `rewritten_data_files`, `added_data_files`, `rewritten_bytes`, `rewritten_manifests`, `added_manifests`, `expired_snapshots`, `deleted_data_files`, `deleted_manifest_files`, `deleted_position_delete_files`, `deleted_equality_delete_files`, summed from SUCCEEDED operation runs' metrics per the spec's key table; `attempts_without_metrics: int` = succeeded operation runs whose metrics are exactly `{"completed_without_callback": 1}`.
- [ ] **Step 1: Failing tests:** repo `test_list_by_table_since_filters_by_created_at`; service `test_storage_splits_current_and_old_snapshot_bytes`, `test_reclaimed_sums_metric_keys` (one run with `rewrite_data_files {"rewritten_data_files_count": 20, "added_data_files_count": 5, "rewritten_bytes_count": 17737}` and `expire_snapshots {"deleted_manifest_lists_count": 22}` → `rewritten_data_files == 20`, `expired_snapshots == 22`), `test_failed_operations_add_nothing`, `test_counts_attempts_without_metrics`; web `test_get_storage_returns_200`.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** tests then full CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(table-maintenance): report a table's storage split and reclaimed space`

### Task 7: Console scaffold and table list

**Files:**
- Create: `src/console/` — `package.json` (scripts `dev`, `build`, `preview`, `typecheck` = `tsc --noEmit`, `lint` = `eslint .`, `test` = `vitest`), `package-lock.json`, `tsconfig.json`, `vite.config.ts` (`base: "/console/"`, dev proxy `/console/api` → `http://localhost:8000` with path rewrite to strip `/console/api`), `eslint.config.js`, `index.html`, `src/main.tsx`, `src/App.tsx` (router with `basename="/console"`), `src/api/client.ts`, `src/api/types.ts`, `src/pages/TableListPage.tsx`, `src/test/setup.ts`, `Dockerfile` (node build stage → `nginx:1.29-alpine` serve stage), `nginx.conf`, `.dockerignore`, `README.md`
- Test: `src/console/src/pages/TableListPage.test.tsx`, `src/console/src/api/client.test.ts`

**Interfaces:**
- Produces: `apiGet<T>(path: string): Promise<T>` and `apiSend<T>(method: "POST" | "PUT", path: string, body?: unknown): Promise<T>` prefixing `/console/api`; non-2xx throws `ApiError { status: number; detail: string }` (detail from the JSON `detail` field). `types.ts` mirrors the API responses of `TableApiResponse`, `TableMaintenanceRunApiResponse` and Tasks 3–6 DTOs field for field (snake_case kept). Routes: `/` → table list, `/tables/:uuid/:tab?` → table page (Task 8). nginx: `location /console/api/ { proxy_pass http://table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000/; }` and `location /console/ { try_files $uri $uri/ /console/index.html; }` with assets under `/usr/share/nginx/html/console/`; listen 8080, non-root.
- [ ] **Step 1: Scaffold** with `npm create vite@latest` equivalents written by hand (pin exact versions in `package.json`), install, and write failing tests: `client.test.ts` — `apiGet` prefixes `/console/api` and throws `ApiError` with `status 404` and the JSON detail; `TableListPage.test.tsx` — with a mocked `fetch` returning two tables, renders both full names, the status filter `PAUSED` leaves one row, the search box filters by substring of `catalog.namespace.table`, each row links to `/tables/<uuid>`.
- [ ] **Step 2: Run** `npm --prefix src/console test -- --run` — Expected: FAIL.
- [ ] **Step 3: Implement** the client, types and list page (columns: name, status, selection, source preset, updated).
- [ ] **Step 4: Run** the console CHECKS and `docker build -t console:dev src/console` — Expected: PASS / image builds.
- [ ] **Step 5: Commit** `feat(console): scaffold the data platform console with the table list`

### Task 8: Table page shell, Commits, Maintenance and Properties tabs

**Files:**
- Create: `src/console/src/pages/TablePage.tsx`, `src/console/src/components/TableHeader.tsx`, `RunMaintenanceDialog.tsx`, `tabs/CommitsTab.tsx`, `tabs/MaintenanceTab.tsx`, `tabs/PropertiesTab.tsx`, `src/console/src/format.ts` (bytes, counts, relative time)
- Test: `TablePage.test.tsx`, `TableHeader.test.tsx`, `tabs/CommitsTab.test.tsx`, `tabs/MaintenanceTab.test.tsx`, `format.test.ts`

**Interfaces:**
- Consumes: Task 7 client and types.
- Produces: tab keys `overview`, `commits`, `maintenance`, `properties`, `settings` (URL segment; missing → `overview`). Header summary numbers come from `metadata` (rows, data files, bytes, average data-file size = bytes / data files, snapshots, relative time of `last_committed_at`). Run maintenance dialog posts `{"operations": [...]}` to `/v1/tables/{uuid}/maintenance` with checkboxes for the four operations, default all checked, confirm text "Runs on the whole table, ignoring thresholds". Pause/Resume posts to `/pause` / `/resume` and refetches the table. The Maintenance tab links each run to `execution_ref` as text (no Temporal URL is configured).
- [ ] **Step 1: Failing tests:** `format.test.ts` (`formatBytes(50540544) === "48.2 MB"`, `formatBytes(0) === "0 B"`); `TableHeader.test.tsx` (renders `1,204,331 rows`, `avg 3.2 MB / file`; Pause button posts `/pause`); `TablePage.test.tsx` (unknown tab segment falls back to Overview; `shows not-in-catalog notice` when `metadata` answers 404 with detail ending `is not in the catalog`, while the header still shows name and status); `CommitsTab.test.tsx` (rows newest first with writer label "Kafka Connect", expanding a row shows the snapshot id and summary JSON; `null` counters render "—"); `MaintenanceTab.test.tsx` (per-operation attempts, metrics and error render).
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** console CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(console): show a table's header, commits, maintenance runs and properties`

### Task 9: Overview tab — Health, Storage, Freshness

**Files:**
- Create: `src/console/src/tabs/OverviewTab.tsx`, `src/console/src/components/HealthPanel.tsx`, `StoragePanel.tsx`, `FreshnessPanel.tsx`, `src/console/src/freshness.ts`
- Test: `HealthPanel.test.tsx`, `StoragePanel.test.tsx`, `freshness.test.ts`, `OverviewTab.test.tsx`

**Interfaces:**
- Consumes: Tasks 3–6 endpoints via Task 7 client; `RunMaintenanceDialog` (Task 8) for Run now with one operation preselected.
- Produces: `hourlyCommitBuckets(commits, now): { hourStart: string; byOperation: Record<string, number> }[]` (24 buckets, oldest first) and `writerMix(commits): Record<string, number>` in `freshness.ts`. Freshness fetches `commits?since=<now−24h ISO>&limit=1000`; `truncated` → counts prefixed "≥ ". Storage is its own query: Overview renders Health and Freshness without waiting for it, Storage shows its own loading and error state. Health lines read e.g. "12 reducible files in 3 partitions, threshold 5" / "in cooldown until …" / "disabled"; not scheduled → banner "The scheduler skips this table: paused" and each line suffixed "(would be due when resumed)" for due lines.
- [ ] **Step 1: Failing tests:** `freshness.test.ts` (commits at now−30m and now−90m → last two buckets have 1 each; writer mix counts); `HealthPanel.test.tsx` (`shows the not-scheduled banner` for `scheduled:false, reason:"paused"`; a due line has "Run now"; a cooldown line has none); `StoragePanel.test.tsx` (old-snapshot bytes shown; `attempts_without_metrics: 2` shows a note); `OverviewTab.test.tsx` (`renders while storage is still loading` — storage fetch never resolves, Health is visible; `renders an empty table` — metadata with `snapshot_count: 0` and empty commits shows "No commits yet").
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** (chart with plain SVG or one small chart library; schema and partition spec tables; last 5 commits; last run).
- [ ] **Step 4: Run** console CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(console): show health, storage and freshness on a table's overview`

### Task 10: Settings tab

**Files:**
- Create: `src/console/src/tabs/SettingsTab.tsx`
- Test: `src/console/src/tabs/SettingsTab.test.tsx`

**Interfaces:**
- Consumes: `GET /v1/tables/{uuid}` (`settings`, `source_preset_id`), `PUT /v1/tables/{uuid}/settings`, `GET /v1/table-maintenance-presets/{id}`.
- Produces: an editor over the settings JSON shape the API returns (per-operation enabled, interval and thresholds as form fields; unknown keys preserved untouched). Save PUTs the whole object; a 422 shows the API detail. Reset to preset GETs the preset and PUTs its settings after a confirm; hidden when `source_preset_id` is null.
- [ ] **Step 1: Failing tests:** saving a changed `min_reducible_files` PUTs the full object with that field changed; a 422 response shows its detail; Reset to preset PUTs the preset's settings; no `source_preset_id` hides the button.
- [ ] **Step 2: Run** — Expected: FAIL.
- [ ] **Step 3: Implement** (read the settings shape from `adapter/inbound/web/table/dto.py` and the settings mapper the API uses).
- [ ] **Step 4: Run** console CHECKS — Expected: PASS.
- [ ] **Step 5: Commit** `feat(console): edit a table's maintenance settings and reset them to the preset`

### Task 11: Deploy the console and extend validation and e2e

**Files:**
- Modify: `platform/25-lakehouse-control-plane/build.sh` (build + load `console` from `src/console`, print `CONSOLE_TAG=`), `bootstrap.sh` (read `CONSOLE_TAG`, `--set image.console.tag=`), `chart/values.yaml` (`image.console.repository: console`, `console.port: 8080`, `console.resources`), `chart/templates/console.yaml` (Deployment, Service `console`, `HTTPRoute` `console` with `parentRefs` `platform-gateway` / `istio-ingress` and `PathPrefix /console`), `validate.sh`, `e2e.sh`, `README.md`
- Modify: `platform/22-polaris-routes/gateway.yaml` (`allowedRoutes.namespaces.selector` → `matchExpressions: [{key: kubernetes.io/metadata.name, operator: In, values: [lakehouse-catalog, lakehouse-control-plane]}]`)
- Modify: `CLAUDE.md` (Project Status: console deployed, history line, wave-25 component list)

**Interfaces:**
- Consumes: Task 7 image, Tasks 3–6 endpoints.
- `validate.sh` additions: `kubectl rollout status deployment/console`; the `console` HTTPRoute is Accepted; through a temporary `kubectl port-forward` of `svc/platform-gateway-istio` in `istio-ingress`, `curl -fsS /console/` contains `<div id="root">`, `curl -fsS /console/tables/x/commits` (deep link) contains `<div id="root">`, `curl -fsS /console/api/v1/tables` is a JSON array.
- `e2e.sh` additions after the existing "after:" measurements: read `metadata`, `commits?limit=1000`, `health`, `storage` of `tm_e2e_orders` through the `api` helper and assert `metadata.total_data_files == ORDERS_FILES_AFTER`, `metadata.snapshot_count == ORDERS_SNAPSHOTS_AFTER`, the newest commit is `committed_at`-ordered first, `health.operations` has four items, `storage.reclaimed.rewritten_data_files >= 20`.
- [ ] **Step 1: Apply** the wave-22 gateway change with `KUBE_CONTEXT=retail-lakehouse bash platform/22-polaris-routes/bootstrap.sh` and run its `validate.sh` — Expected: Polaris route still Accepted.
- [ ] **Step 2: Implement** chart, build, bootstrap, validate, e2e, README changes.
- [ ] **Step 3: Deploy** `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh`, then `validate.sh` — Expected: "Lakehouse control plane is ready".
- [ ] **Step 4: Run** `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh` — Expected: "Table maintenance e2e passed".
- [ ] **Step 5: Commit** `feat(lakehouse-control-plane): deploy the console behind the platform gateway` (wave 22 gateway, wave 25, CLAUDE.md), then a separate `docs(console): …` commit only if README needs more than the deploy notes.
