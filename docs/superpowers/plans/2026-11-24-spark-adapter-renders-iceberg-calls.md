# Spark Adapter Renders Iceberg Calls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The domain decides what a maintenance job does: its settings and which partitions it compacts, as typed content. The k8s Spark adapter alone writes Iceberg's procedure arguments, their time strings and the `where` Spark SQL, and the `CALL` Spark runs stays byte-identical.

**Architecture:**
- The domain gains a typed content value object per operation and a `PartitionSelection` (spec plus partition values), which `select_partitions` builds with the validation `build_partition_filters` had, minus the text.
- The run stores that content in place of `filters` and `procedure_args`. Planning, the Temporal payload, the database row and the API carry it.
- The submit port takes primitive-only typed job dataclasses. The k8s adapter turns them into the same `GLAC_REQUEST` (`where` list and `procedure_args` dict) it builds today, so the Spark runtime is unchanged.

**Tech Stack:** Python 3.14, Pydantic v2 (domain), frozen dataclasses (outbound port), Temporal Python SDK, SQLAlchemy JSON columns, FastAPI, React + orval generated client, Storybook.

**Spec:** Linear KCL-109 ("維護參數的 Iceberg 拼法和 where 條件改由 Spark adapter 產生，domain 只決定要做什麼"), with its completion conditions.

## Global Constraints

- The `CALL` statements Spark runs do not change by one character for the same policy and table. The adapter produces the same `GLAC_REQUEST` `where` and `procedure_args` it does today, and `src/data-platform/runtime/spark/` is not touched.
- Options remain domain (user-chosen, with business rules, named as ADR 0012 says); Iceberg's call format (hyphenated option names, which values go in the `options` map, time as an ISO string with `+00:00`) and the `where` Spark SQL, escaping included, live only in the Spark adapter.
- Gateway input files stay primitive-only dataclasses (`str`, `int`, `float`, `bool`, `None`, `list`/`tuple`/`dict`, plus `datetime`, their own gateway directory's extra files); no Pydantic and no `application.domain` import in the port.
- No compatibility code, no migration of stored runs (KCL-110): the cluster is rebuilt afterwards.
- Reading a run's record still shows which settings it used and which partitions it compacted, with no less information than today.
- One object per file; `from __future__ import annotations`; `tuple[...]` for inbound port sequences; import-linter has no exceptions.

## Review Focus

- A string partition value holding a quote or a backslash (`o'neil`, `a\b`) must render to the same `where` text as today. A golden case pins it in Task 1.
- A table whose partition spec evolved, with partitions selected under two spec ids, must give one `where` per spec, ordered by spec id. Golden case in Task 1.
- A selection the old builder refused must still make the run compact the whole table, with the same warning, not fail at submit time. Examples are an unsupported transform, a nanosecond type, `hour` on a date, an out-of-range day, and a spec of only `void` fields. Parity tests in Task 2, a planner test in Task 4.
- A manual run of an operation the policy leaves out must keep the platform's defaults: target file size only, no manifest options, the table property retention, orphans older than 3 days. Golden cases in Task 1.
- An `older_than` computed from a non-UTC `now` with microseconds must keep today's ISO text: converted to UTC, `+00:00`, microseconds kept. A golden case in Task 1, and a database round-trip test in Task 4 checking the time zone and microseconds.

---

### Task 1: Pin today's Spark request

**Files:**
- Create: `src/data-platform/backend/tests/context/table_maintenance/adapter/outbound/table_maintenance_run/k8s/spark_request_cases.py`
- Create: `src/data-platform/backend/tests/context/table_maintenance/adapter/outbound/table_maintenance_run/k8s/spark_request_golden.json`
- Test: `src/data-platform/backend/tests/context/table_maintenance/adapter/outbound/table_maintenance_run/k8s/test_spark_request_golden.py`

**Interfaces:**
- Produces:
  - `SPARK_REQUEST_CASES: tuple[SparkRequestCase, ...]`, where `SparkRequestCase` is a frozen dataclass with `name: str`, `operation: MaintenanceOperation`, `policy: MaintenancePolicyContent`, `properties: dict[str, str]`, `now: datetime`, `catalog: str`, `specs: tuple[PartitionSpecInfo, ...]` and `partitions: tuple[PartitionStats, ...]`.
  - The golden JSON, an object keyed by case name, each value `{"where": [...], "procedure_args": {...}}`.
  - `render(case) -> dict` in the test module. Tasks 1–3 implement it with today's functions; Task 4 rewrites it onto the new path.

- [ ] **Step 1:** Write the cases. Each is a whole planning input, and together they cover:
  - `rewrite_data_files`:
    - every option set, with the sort strategy and a sort order;
    - the policy leaving the operation out;
    - an identity string partition `o'neil` and another `a\b`;
    - `day(ts)` plus `bucket[16](id)` on a `timestamptz`;
    - an evolved spec with partitions under spec ids 0 and 1;
    - `month` and `year` on a date, `hour` on a `timestamp`;
    - `truncate[4]` on a string, a null value, a boolean, a decimal, a double and a long;
    - a nested column `a.b` and a catalog name with a backtick.
  - `rewrite_manifests`: with `use_caching`, and with the policy leaving it out.
  - `expire_snapshots`: with options and an explicit target, and with the policy leaving it out (retention from the table properties).
  - `remove_orphan_files`: with options, and with the policy leaving it out.
  - One `now` in `+08:00` with microseconds, used by the expire and orphan cases.
- [ ] **Step 2:** Write `test_spark_request_golden.py`:
  - `render(case)` returns today's two pieces of the request. `procedure_args` is `maintenance_procedure_args(case.operation, case.policy, case.properties, case.now)`. `where` is `[f.where for f in build_partition_filters(case.catalog, case.specs, case.partitions)]`, or `[]` when there are no partitions.
  - The test is parametrized over the cases and asserts `render(case) == golden[case.name]`.
  - It also asserts `set(golden) == {c.name for c in SPARK_REQUEST_CASES}`.
- [ ] **Step 3:** Generate the golden JSON once from `render`, written with `json.dumps(..., indent=2, sort_keys=False)`. Key order is kept because the order of the `options` map becomes the order of `map(...)` in the `CALL`. Read the file and check by eye that the quote, backslash, `+00:00` and microsecond cases look right.
- [ ] **Step 4:** Run `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/adapter/outbound/table_maintenance_run/k8s/test_spark_request_golden.py -v`. Expected: PASS. This is a characterization test: it passes on today's code by design.
- [ ] **Step 5:** Commit `test(adapter): pin the Spark request today's planning produces (KCL-109)`.

### Task 2: The domain names what a job does

**Files:**
- Create: `context/table_maintenance/application/domain/model/shared/partition_selection.py`, exported from `shared/__init__.py`
- Create: `context/table_maintenance/application/domain/service/table/select_partitions.py`, exported from its package
- Create in `context/table_maintenance/application/domain/model/table_maintenance_run/`:
  - `rewrite_data_files_job_content.py`
  - `rewrite_manifests_job_content.py`
  - `expire_snapshots_job_content.py`
  - `remove_orphan_files_job_content.py`
  - `maintenance_job_content.py` (the union alias)
  - `maintenance_job_content_from_primitives.py`
  - Export all of them from the package.
- Test:
  - `tests/context/table_maintenance/application/domain/model/shared/test_partition_selection.py`
  - `tests/context/table_maintenance/application/domain/service/table/test_select_partitions.py`
  - `tests/context/table_maintenance/application/domain/model/table_maintenance_run/test_maintenance_job_content.py`

**Interfaces:**
- Produces:
  - **`PartitionSelection(ValueObject)`**: `spec: PartitionSpecInfo` and `values: tuple[tuple[str | int | float | bool | None, ...], ...]`. Its invariants (each raises `InvariantViolation`):
    - `values` is not empty;
    - each tuple has `len(spec.fields)` values;
    - the spec is not `is_unpartitioned`.
  - **`select_partitions(specs: Sequence[PartitionSpecInfo], partitions: Sequence[PartitionStats]) -> tuple[PartitionSelection, ...]`**:
    - groups the partitions by spec, one selection per spec id, sorted by spec id;
    - returns `()` when any selected partition belongs to an unpartitioned spec (the whole table);
    - raises `ValueError` exactly where `build_partition_filters` raises today, with the same messages.
  - **`RewriteDataFilesJobContent(ValueObject)`**:
    - `operation: Literal[MaintenanceOperation.REWRITE_DATA_FILES] = MaintenanceOperation.REWRITE_DATA_FILES`
    - `target_file_size_bytes: PositiveInt`
    - `options: RewriteDataFilesOptions = Field(default_factory=RewriteDataFilesOptions)`
    - `partitions: tuple[PartitionSelection, ...] = ()`, whose spec ids must be unique.
  - **`RewriteManifestsJobContent`**: `operation` and `options: RewriteManifestsOptions` (empty by default).
  - **`ExpireSnapshotsJobContent`**: `operation`, `older_than: AwareDatetime`, `retain_last: PositiveInt` and `options: ExpireSnapshotsOptions` (empty by default).
  - **`RemoveOrphanFilesJobContent`**: `operation`, `older_than: AwareDatetime` and `options: RemoveOrphanFilesOptions` (empty by default).
  - **`MaintenanceJobContent`**: the union of those four types.
  - **`maintenance_job_content_from_primitives(data: Mapping[str, Any]) -> MaintenanceJobContent`**: dispatches on `data["operation"]` to that class's `from_primitives`, and raises `ValueError` for a missing or unknown operation.

- [ ] **Step 1:** Write the failing tests:
  - **`test_select_partitions.py`:**
    - Each refusal case of `test_build_partition_filters.py` becomes a `pytest.raises(ValueError, match=<same message>)` case of `select_partitions`.
    - The grouping and sorting is a case, and so is an all-`void` spec giving `()`.
  - **`test_partition_selection.py`:** the three invariants.
  - **`test_maintenance_job_content.py`:**
    - a `to_primitives()` → `maintenance_job_content_from_primitives` round trip per operation, keeping a `+08:00` `older_than` equal;
    - a naive `older_than` refused;
    - unset options left out of `to_primitives()`;
    - duplicate spec ids refused;
    - an unknown operation refused.
- [ ] **Step 2:** Run the three files. Expected: FAIL on import (the modules do not exist).
- [ ] **Step 3:** Implement. `select_partitions` performs `build_partition_filters`'s checks in the same order, without producing text:
  - value count;
  - void skipped;
  - nanosecond rejection before the null check;
  - the integer, number, decimal, string and boolean checks per source type;
  - the time-transform type rules;
  - the `_period_bounds` range check.
  Leave `build_partition_filters` in place; Task 4 deletes it.
- [ ] **Step 4:** Run the three files and the whole domain test folder. Expected: PASS.
- [ ] **Step 5:** Commit `feat(domain): typed maintenance job content and partition selections (KCL-109)`.

### Task 3: The submit port's typed job and the Spark rendering

**Files:**
- Create in `context/table_maintenance/application/port/outbound/table_maintenance_run/submit_maintenance_job/`, exported from its `__init__.py` and from `port/outbound/table_maintenance_run/__init__.py`:
  - `job_partition_field.py`
  - `job_partition_spec.py`
  - `rewrite_data_files_job.py`
  - `rewrite_manifests_job.py`
  - `expire_snapshots_job.py`
  - `remove_orphan_files_job.py`
- Create in `context/table_maintenance/adapter/outbound/table_maintenance_run/k8s/`:
  - `iceberg_procedure_args.py`
  - `spark_partition_where.py`
  - `spark_where_clauses.py`
- Modify:
  - `tests/architecture/test_outbound_port_structure.py`: `GATEWAY_EXTRA_FILES` gains the six file names. `from datetime` joins the allowed prefixes. `input.py` and the extra files may import their own gateway directory's extra files, as `output.py` already may.
  - Backend `CLAUDE.md`: the outbound port rules (the paragraph "Input/output files must only use primitive types …").
- Test:
  - `tests/.../k8s/test_iceberg_procedure_args.py`
  - `tests/.../k8s/test_spark_partition_where.py`
  - `tests/.../k8s/test_spark_where_clauses.py`
  - The new architecture cases in `test_outbound_port_structure.py`.

**Interfaces:**
- Produces (all frozen dataclasses):
  - **`JobPartitionField`**: `source_column: str`, `source_type: str`, `transform: str`.
  - **`JobPartitionSpec`**: `spec_id: int`, `fields: tuple[JobPartitionField, ...]` and `values: tuple[tuple[str | int | float | bool | None, ...], ...]`.
  - **`RewriteDataFilesJob`**:
    - `target_file_size_bytes: int`
    - `partitions: tuple[JobPartitionSpec, ...] = ()`
    - each of the ten `RewriteDataFilesOptions` fields under the same name, defaulting to `None` (`strategy: str | None` holds the enum value).
  - **`RewriteManifestsJob`**: `use_caching: bool | None = None`.
  - **`ExpireSnapshotsJob`**: `older_than: datetime`, `retain_last: int`, `max_concurrent_deletes: int | None = None`, `stream_results: bool | None = None`.
  - **`RemoveOrphanFilesJob`**: `older_than: datetime`, `max_concurrent_deletes: int | None = None`, `prefix_mismatch_mode: str | None = None`.
  - **No alias file for the union.** An extra gateway file must define one class named after its stem, so the four-way union `RewriteDataFilesJob | RewriteManifestsJob | ExpireSnapshotsJob | RemoveOrphanFilesJob` is spelled out where it is used (`input.py`, the adapter functions, `gateway_job_of`).
  - **`iceberg_procedure_args(job) -> dict[str, Any]`**: the old `maintenance_procedure_args` output shape, key order included:
    - `rewrite_data_files`: `strategy`, then `sort_order`, then `options` (with `target-file-size-bytes` first, then the options in today's `procedure_options` order);
    - `expire_snapshots`: `older_than`, `retain_last`, then its options;
    - `remove_orphan_files`: `older_than`, then its options;
    - `rewrite_manifests`: `use_caching` or nothing;
    - `older_than` is written as `job.older_than.astimezone(UTC).isoformat()`.
  - **`spark_partition_where(catalog: str, spec: JobPartitionSpec) -> str`**: today's `_spec_where` with the catalog quoted, clauses de-duplicated and sorted. It raises `ValueError` on what it cannot render.
  - **`spark_where_clauses(catalog: str, job) -> list[str]`**: one `where` per partition spec ordered by spec id for a `RewriteDataFilesJob` with partitions, otherwise `[]`.

- [ ] **Step 1:** Write the failing tests:
  - **`test_spark_partition_where.py`:** each text-producing case of `test_build_partition_filters.py`, with its expected SQL copied verbatim, built from `JobPartitionSpec`.
  - **`test_iceberg_procedure_args.py`:** each case of `test_maintenance_procedure_args.py`, with its expected dict copied verbatim, built from the typed job. Add a `+08:00` microsecond `older_than` case.
  - **`test_spark_where_clauses.py`:** ordering by spec id, `[]` without partitions, `[]` for the three other jobs.
  - **Architecture tests:** an extra file importing a sibling extra file is allowed; `input.py` importing one is allowed; an import from `application.domain` still fails.
- [ ] **Step 2:** Run them. Expected: FAIL on import.
- [ ] **Step 3:** Implement. Move the rendering helpers of `build_partition_filters.py` into `spark_partition_where.py` unchanged; the domain copy stays until Task 4.
- [ ] **Step 4:** Run the new tests plus `tests/architecture`. Expected: PASS.
- [ ] **Step 5:** Commit `feat(adapter): the Spark adapter renders Iceberg procedure arguments and where clauses (KCL-109)`.

### Task 4: Runs carry typed content end to end

**Files:**
- Create:
  - `tests/architecture/test_no_engine_spelling_in_application.py`
  - `context/table_maintenance/application/service/table_maintenance_run/maintenance_job_content.py` (replaces `maintenance_procedure_args.py`)
  - `context/table_maintenance/application/service/table_maintenance_run/gateway_job_of.py`
- Delete:
  - `maintenance_procedure_args.py` and its test
  - `domain/service/table/build_partition_filters.py` and its test
  - `domain/model/shared/spec_filter.py`
  - the `procedure_arguments()` and `procedure_options()` methods of the four options objects, and their cases in `test_operation_options.py`
- Modify:
  - `domain/model/table_maintenance_run/table_maintenance_run.py`: `content: MaintenanceJobContent` replaces `filters` and `procedure_args`. Its invariant is `content.operation is operation`, which replaces `_misplaced_filters`. `create(..., content)` makes `content` required.
  - `service/table/plan_table_maintenance.py`: `_partitions_of` uses `select_partitions` with today's fallback and warning; `Operation.content` comes from `maintenance_job_content`.
  - Port outputs:
    - `port/inbound/table/plan_table_maintenance/output.py`: `Operation.content: dict[str, Any]`; `Filter` is removed.
    - `port/inbound/table_maintenance_run/create_table_maintenance_runs/input.py`: `Run.content: dict[str, Any]`; `Filter` is removed.
    - the get and list run outputs: `content: dict[str, Any]`.
    - `table_maintenance_run_output_fields.py`.
  - `service/table_maintenance_run/create_table_maintenance_runs.py` (including `_require_stored_as_planned`) and `submit_maintenance_operation.py`.
  - `port/outbound/table_maintenance_run/submit_maintenance_job/input.py`: `job: RewriteDataFilesJob | RewriteManifestsJob | ExpireSnapshotsJob | RemoveOrphanFilesJob` replaces `where` and `procedure_args`.
  - `adapter/outbound/table_maintenance_run/k8s/spark_application_manifest.py`: `GLAC_REQUEST` is built explicitly with today's keys in today's order: `run_id`, `operation`, `attempt`, `catalog`, `namespace`, `table`, `where`, `procedure_args`, `result_report_url`, `size`, `priority`, `app_name`. `where` comes from `spark_where_clauses` and `procedure_args` from `iceberg_procedure_args`.
  - `adapter/hybrid/temporal/inbound/workflows/table_reconciliation_workflow.py`: it passes `"content": op["content"]`.
  - SQL: `table_maintenance_runs_table.py` (`content_json` replaces `filters_json` and `procedure_args_json`) and `table_maintenance_run_row_mapper.py`.
  - `service/table/list_table_commits.py`: its output carries `datetime`, and the web adapter writes the same ISO text as today. This closes the one other time-string format in `application/` that the guard would flag.
  - Web:
    - `adapter/inbound/web/table_maintenance_run/dto.py`: `settings: dict[str, Any]` and `partitions: list[TableMaintenanceRunPartitionsApiResponse]` replace `filters` and `procedure_args`.
    - New `adapter/inbound/web/table_maintenance_run/partition_value_text.py`.
    - `openapi.json` and the generated client, via `task dev:generate-api`.
  - Console:
    - `src/data-platform/frontend/src/lib/compactionScopeText.ts` and its test;
    - `components/tabs/MaintenanceRunPanel.tsx`, which shows "Parameters" from `settings`;
    - `MaintenanceTab.test.tsx`;
    - `src/stories/storyData.ts`.
  - Golden test `render`: built from `maintenance_job_content` + `select_partitions` + `gateway_job_of` + `spark_where_clauses` / `iceberg_procedure_args`. The golden JSON is not edited.

**Interfaces:**
- Consumes: Task 2's domain types, and Task 3's job dataclasses and render functions.
- Produces:
  - `maintenance_job_content(operation: MaintenanceOperation, policy: MaintenancePolicyContent, properties: Mapping[str, str], now: datetime, partitions: tuple[PartitionSelection, ...] = ()) -> MaintenanceJobContent`. It applies today's resolution: the target file size from the properties, the retention from the target or the properties, and orphans older than 3 days by default. `older_than` is `now - age`, and a naive `now` raises `ValueError`.
  - `gateway_job_of(content: MaintenanceJobContent) -> RewriteDataFilesJob | RewriteManifestsJob | ExpireSnapshotsJob | RemoveOrphanFilesJob`.
  - The API run response:
    - `settings`: the content's `to_primitives()` without `operation` and `partitions`.
    - `partitions: [{"spec_id": int, "partitions": [[{"field": source_column, "transform": str, "value": str}]]}]`, where `value` comes from `partition_value_text(transform, source_type, value)`, using Iceberg's human forms:
      - `null` for None;
      - year `2026`, month `2026-11`, day `2026-11-20`, hour `2026-11-20-10`;
      - identity date and timestamp values as ISO text;
      - booleans `true` / `false`;
      - anything else `str(value)`.

- [ ] **Step 1:** Write the guard `test_no_engine_spelling_in_application.py` (RED on today's code). It scans every `context/*/application/**/*.py` and flags:
  - a string constant equal to an Iceberg procedure option name. The documented `rewrite_data_files` set is: `target-file-size-bytes`, `min-input-files`, `min-file-size-bytes`, `max-file-size-bytes`, `partial-progress.enabled`, `partial-progress.max-commits`, `partial-progress.max-failed-commits`, `max-concurrent-file-group-rewrites`, `rewrite-all`, `rewrite-job-order`, `use-starting-sequence-number`, `delete-file-threshold`, `delete-ratio-threshold`, `remove-dangling-deletes`, `max-file-group-size-bytes`, `output-spec-id`, `max-files-to-rewrite`, `compression-factor`, `shuffle-partitions-per-file`;
  - a string constant containing a Spark SQL marker: a backtick, `.system.`, ` IS NULL`, `DATE '`, `TIMESTAMP '`, or `TIMESTAMP_NTZ '`;
  - a call to a method named `isoformat` or `strftime`;
  - a function or method whose name starts with `procedure_`.

  It also holds a self-test with one snippet per rule, and a negative case: the table property `write.target-file-size-bytes` and the summary key `added-data-files` are not flagged.
- [ ] **Step 2:** Run it. Expected: FAIL, naming `rewrite_data_files_options.py`, `maintenance_procedure_args.py`, `build_partition_filters.py` and `list_table_commits.py`.
- [ ] **Step 3:** Write the other failing tests first:
  - `test_maintenance_job_content.py`, ported from the deleted procedure-args test and asserting typed content;
  - `test_gateway_job_of.py`;
  - `test_partition_value_text.py`;
  - a row-mapper round trip of each content kind, an `older_than` of `+08:00` with microseconds read back equal;
  - a run invariant refusing content of another operation;
  - a planner case where a selection `select_partitions` refuses gives empty partitions and logs the warning;
  - the create-runs and submit service cases on `content`;
  - the route test on `settings` and `partitions`;
  - the workflow payload test on `content`;
  - the console tests on the new fields.

  Update the existing tests that build runs or plans with `filters` or `procedure_args`.
- [ ] **Step 4:** Implement. Then run `task dev:generate-api` and the console's `npm run typecheck`.
- [ ] **Step 5:** Run the guard, the golden test (with the JSON unchanged), the whole backend suite, `ty check`, `ruff check .`, `lint-imports` and `task gates:pre-pr`. Expected: all pass.
- [ ] **Step 6:** Commit `refactor(table-maintenance): runs carry typed job content and the Spark adapter writes the call (KCL-109)`.

### Task 5: Record the decision

**Files:**
- Create: `docs/adr/0016-the-spark-adapter-writes-iceberg-procedure-calls.md`
- Modify:
  - `docs/adr/0004-spark-sql-literal-escaping.md`: its status says the placement in the domain is superseded by ADR 0016, and the escaping rule stands.
  - `docs/adr/0012-*.md`: the `options` decision line says options are domain values, and their Iceberg spelling is written by the Spark adapter.
  - Root `CLAUDE.md`: the ADR list gains 0016.
  - Backend `CLAUDE.md`: the run model paragraph (`content`), and the rule that `application/` holds no Iceberg call spelling, guarded by `test_no_engine_spelling_in_application.py`.
  - `docs/agents/project-history.md`: one line.
- [ ] **Step 1:** Write the ADR: its context (KCL-109, F3), the decision (the four placements above), its consequences (adding an option is the domain field plus the adapter's spelling; the run record shows domain names; stored runs are not migrated), and its references (ADR 0004, ADR 0012, the Iceberg Spark procedures docs).
- [ ] **Step 2:** Commit `docs(adr): the Spark adapter writes Iceberg procedure calls (KCL-109)`.
