# Schema and Partition Spec Version Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The table page's Schema tab lists every schema and partition spec version of an Iceberg table, says what each changed against the one before ("+1 added · 1 type changed"), shows the comparison of any two versions as one list matched by field id, and the Commits tab links each commit to the schema version it was written with.

**Architecture:** The catalog context's `Table` aggregate keeps every schema and partition spec Polaris returns (not only the current ones), every schema field keeps its nested fields with their Iceberg ids, and each snapshot keeps its `schema-id`. Two domain services in the catalog context compare two schemas by field id and two partition specs by partition field id (pairing a dropped and an added field on the same source column as one transform change). Four new catalog read endpoints serve the version lists and the comparisons, computed per request from Polaris, never cached. The design system gains a generic `DiffList`; the console builds the Schema tab's version lists and comparisons from it, and the Commits tab shows a `v<N>` link from the table-maintenance commits API, which gains `schema_id`.

**Tech Stack:** Python 3.14, Pydantic (strict `ValueObject` / `UseCaseOutput`), FastAPI, httpx (Polaris REST), PyIceberg (table maintenance commits), React + TanStack Query + orval + MSW, Radix (`Switch`), Tailwind 4, Storybook 10 browser tests with axe.

**Spec:** Linear KCL-97 (https://linear.app/kcl10/issue/KCL-97, no comments), with the screen decided in the KCL-79 comments of 2026-11-17 and 2026-11-19 (https://linear.app/kcl10/issue/KCL-79).

**Refreshed 2026-11-20 against HEAD `bfdc0987`** (KCL-93 and KCL-91 built). **Order:** KCL-96 (`docs/superpowers/plans/2026-11-20-overview-metric-trends.md`) is implemented first, then this plan. Where both change a file, this plan starts from KCL-96's committed version (list under Global Constraints). **Read each file at HEAD before changing it; never apply a step against a remembered version.**

## Global Constraints

Decided by the issue (copied):

- Version list on the Schema tab, each version marked with what it changed against the previous one; only the newest 10 shown, older ones folded behind "Show N earlier versions".
- Clicking a version shows its comparison with the previous version; the user may also pick any two versions.
- Comparison matched by field id, never by name; one list, no side-by-side; added, removed, renamed and type-changed fields; nested fields show their full path; a "Show changes only" switch.
- Partition specs use the same presentation, mark the default spec, and write a transform change as `day(order_ts) → hour(order_ts)`.
- DDL shows only the current schema and says so.
- The Commits tab shows each commit's schema as `v<N>`, linking to the Schema tab with that version selected.
- Not built: how much data each spec still holds; sort order evolution.
- Comparisons are computed in the catalog context's domain. The diff list is a generic design-system component. The catalog context reads Polaris on every request and caches nothing.

Decided here (each with its reason):

- **Versions are named by their Iceberg id: `v0`, `v1`, … for schemas, the same for partition specs.** The labels then match the ids Spark and Trino show in `$metadata` tables and in `schema-id`; the first schema is `v0`.
- **"Previous version" is the version with the next lower id, and the list is ordered by id, newest (highest) first.** Iceberg does not record when a schema was made (KCL-79, 11/17), and it reuses an existing schema id when a change produces a schema it already has, so the current schema may not be the highest id: the `Current` badge and the default selection follow `current-schema-id` / `default-spec-id`, not the list's top.
- **The first version has no comparison: every field is listed unchanged and its summary reads "First version".** Marking every field of a new table as added would make the first version look like the biggest change.
- **Change kinds beyond the issue's four: `nullability_changed` and `doc_changed`.** Iceberg's schema update API changes requiredness (`makeColumnOptional`, `requireColumn`) and docs (`updateColumnDoc`) as first-class changes; DataHub's schema history reports both. Column reordering is not reported (order is not a field change).
- **Nested paths use Iceberg's full names** (`TypeUtil.indexByName`): a struct child is `parent.child`, a list element `parent.element`, a map's `parent.key` and `parent.value`. The API carries a path as a list of segments, so a name containing a dot stays unambiguous; the console joins them with `.`.
- **A nested field's type in a comparison is its outer type (`struct`, `list`, `map`)**; its children are rows of their own, so a child's change is never also reported as a change of its parent.
- **A renamed parent does not mark its children renamed**; their rows show the new path with the old one as `previous_path`.
- **A removed field is placed right after the nearest field before it in the base version that is still in the list (first if none)**, so removals read in place, as in a code diff.
- **Partition fields are matched by partition field id; then a removed and an added field on the same source column become one `transform_changed` row** (field id = the new one, `previous_field_id` = the old one). Iceberg gives a field with a new transform a new partition field id, so matching by id alone would show `day → hour` as one removal and one addition. A field whose transform became `void` (format v1's way of dropping a partition field) counts as removed; a field that is `void` in both versions is left out.
- **A partition field's expression is `<transform>(<source path>)`** (`day(order_ts)`, `bucket[16](customer_id)`, `identity(region)`): Iceberg's own `PartitionField` text form. The source path comes from the current schema, else from the newest schema holding that field id, else `#<id>`.
- **API shape:** four new routes under `/v1/catalogs/{catalog}/namespaces/{namespace}/tables/{table}`: `GET schema-versions`, `GET schema-versions/{schema_id}/comparison?base=<id>`, `GET partition-spec-versions`, `GET partition-spec-versions/{spec_id}/comparison?base=<id>`. `base` omitted means the previous version. An unknown version or base is 404. The table response itself only gains `schema_id` on each snapshot; it does not carry every schema, so the page's main request stays the same size however long the history is.
- **Use case verbs `List` and `Get`** (`ListTableSchemaVersions`, `GetTableSchemaComparison`, …): both are in `KNOWN_VERBS`; "Compare" is not, and these are reads.
- **The Commits tab's schema id comes from the table-maintenance commits API** (`GET /v1/tables/{uuid}/commits` gains `schema_id`), read by PyIceberg from the same Iceberg metadata as the commit itself: each row then carries its own version, under every filter and page, without joining a second request.
- **Diff markers are text and neutral badges, never status colours** (`src/design-system/CLAUDE.md`: status colours are for status only). A row shows a sign (`+`, `−`, `~`), a `Badge` naming the change, and a removed row's label struck through in `text-on-surface-variant`.
- **The Schema tab's selection lives in the url** (`?schema=5&base=3&only_changes=1&spec=1&spec_base=0&spec_only_changes=1`, `replace` navigation), so a comparison can be shared and survives a reload (console rule for filter state).
- **Phones:** the version list stacks above the comparison below 768px; long paths and types wrap (`break-all`); no horizontal page scroll.
- **KCL-93 and KCL-91 are built (refreshed 2026-11-20).** Compaction rounds and candidates, `/v1/compaction-rounds*`, `/v1/scheduler-settings`, `/v1/tables/{uuid}/compaction-candidates`, the Compaction Rounds page, the Candidates tab and admission are gone (`TablePage`'s tabs are Overview, Schema, Properties, Commits, Maintenance, Reconciliations; an old `/candidates` url falls back to the Overview); `/v1/platform-settings` lives under `table_maintenance_run`. KCL-91's policy shape (`description`, `on`, `dry_run`, four `{target, options}` blocks), cooldown settings, commit window and the `table_managed` wake reason are not read by anything here. The catalog context, the design system's `List`, `Badge`, `Switch`, `Select`, `TextLink` and `Tooltip`, and the console's `SchemaTab` / `CommitsTab` are unchanged since this plan was written; the design system's `FieldProps.description` is now a `ReactNode` (no effect here: `DiffList` has its own props). No decision below changed.
- **Cluster access (refreshed 2026-11-20).** Wave 13 gates every gateway path but `/polaris` behind a Keycloak session, so the verification's API calls through the gateway use `gateway::curl <path>` (source `scripts/utils/gateway.sh` with `KUBE_CONTEXT=retail-lakehouse`; it gets a `platform-validate` token) instead of a bare `curl`, and the console logs in as `platform-admin` (password in Secret `identity/keycloak-clients`).
- **Builds on KCL-96 (refreshed 2026-11-20; `TM` / `FE` as in File Structure).** These files are changed by KCL-96 first; each step here edits KCL-96's committed version, never the HEAD `bfdc0987` one:
  - `TM/adapter/inbound/web/table/dto.py` (KCL-96 removes `TableHealthApiResponse`, `TableHealthOperationApiResponse`, `TableStorageApiResponse` and adds the metrics DTOs; Task 6 adds `schema_id` to `TableCommitApiResponse` there);
  - `tests/context/table_maintenance/adapter/outbound/table/pyiceberg/test_read_table_metadata_pyiceberg_gateway.py` (KCL-96 adds count tests and removes the `measure_storage` tests);
  - `src/data-platform/backend/openapi.json` and `src/data-platform/frontend/src/api/generated/` (regenerated with `GENAPI` on top of KCL-96's routes);
  - `FE/pages/TablePage.test.tsx` (KCL-96's `stubTable` has no `health` / `storage` stubs and answers `metrics/current` and `metrics*`; Task 8 adds the four version routes to it);
  - `FE/pages/TablePage.stories.tsx`, `FE/stories/storyData.ts`, `FE/stories/lakehouseHandlers.ts` (KCL-96 adds `ORDERS_CURRENT_METRICS`, `ORDERS_METRIC_TRENDS`, two metrics handlers and the `Overview*` stories; Tasks 8 and 9 add theirs beside them);
  - `src/data-platform/backend/CLAUDE.md`, `src/data-platform/frontend/CLAUDE.md`, `docs/agents/project-history.md` (one more paragraph, bullet and line each, after KCL-96's).
  `FE/pages/TablePage.tsx` and `FE/components/tabs/OverviewTab.tsx`: KCL-96 does not change `TablePage.tsx`; nothing here touches `OverviewTab.tsx`.
- No new dependency, no data migration, no ADR (the decisions follow KCL-79 and ADRs 0005, 0009, 0010).
- Follow `CLAUDE.md`: TDD, one object per file, `from __future__ import annotations`, StrEnum, ABC ports, `uv run`, never `cd`, `kubectl <verb>` first, never `--no-verify`, never `sops`, never edit `.claude/settings*.json`, explicit paths in `git add`, never run two test suites at once.
- Every commit passes `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=<side>` (`backend`, `frontend`, or `all` when the generated client changes). After a DTO change run `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api` and commit `src/data-platform/backend/openapi.json` and `src/data-platform/frontend/src/api/generated/` with it.
- Commit messages end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.

## Review Focus

- A table whose current schema is not its highest id (Iceberg reused schema 1 after schema 2): the list stays in id order, `Current` sits on `v1`, and the tab opens on `v1` compared with `v0`, not on `v2`. Test in Task 2 (aggregate) and Task 8 (console).
- A column renamed and promoted in the same version (`customer_id: int` → `customer: long`) is one row with `Renamed` and `Type changed`, never a removal plus an addition. Test in Task 3.
- A Commits link or a typed url naming a version the table no longer has (`?schema=9`, `?schema=abc`): the tab shows the current version with the line "Schema v9 is not in this table's history; showing the current schema (v1).", never an error page; the API's 404 for that comparison is not requested. Test in Task 8.
- Format v1 metadata (no `schemas`, no `partition-specs`, snapshots without `schema-id`): one schema version and one spec version, each "First version", and the Commits tab shows no schema link for those commits. Tests in Tasks 2, 6 and 9.
- A v1 partition field dropped by turning it into `void` shows as removed (`day(order_ts)` struck through), not as `day(order_ts) → void(order_ts)`. Test in Task 4.

---

## File Structure

Backend paths are relative to `src/data-platform/backend/`; `CAT` = `context/catalog`, `TM` = `context/table_maintenance`; tests mirror under `tests/`. Console paths are relative to `src/data-platform/frontend/src/` (`FE`), design system to `src/design-system/src/` (`DS`).

| File | Responsibility |
|---|---|
| `CAT/application/domain/model/shared/schema_field.py` | `children`, `outer_type` |
| `CAT/application/domain/model/shared/schema_field_at_path.py` (new), `schema.py` | `SchemaFieldAtPath`, `Schema.walk()` |
| `CAT/adapter/outbound/shared/polaris/iceberg_schema_from_polaris.py` | nested fields with their ids |
| `CAT/application/domain/model/table/table.py`, `snapshot.py`, `partition_spec.py` | every schema and spec, `schema_id` per snapshot, version lookups |
| `CAT/adapter/outbound/table/polaris/table_schemas_from_polaris.py`, `partition_specs_from_polaris.py` (renamed from the singular mappers), `snapshot_from_polaris.py`, `table_from_polaris.py` | keep every schema, spec and snapshot schema id |
| `CAT/application/domain/model/table/schema_change.py`, `schema_field_comparison.py`, `schema_comparison.py` (new) | schema comparison value objects |
| `CAT/application/domain/model/table/partition_change.py`, `partition_field_comparison.py`, `partition_spec_comparison.py` (new) | partition comparison value objects |
| `CAT/application/domain/service/table/compare_schemas.py`, `compare_partition_specs.py` (new) | the two comparisons |
| `CAT/application/port/inbound/table/{list_table_schema_versions,get_table_schema_comparison,list_table_partition_spec_versions,get_table_partition_spec_comparison}/` (new) | ports |
| `CAT/application/service/table/` four services + `load_table.py` (new) | use cases |
| `CAT/adapter/inbound/web/table/router.py`, `dto.py`; `CAT/adapter/inbound/web/shared/web_use_cases.py`; `bootstrap/container/build_catalog_web_use_cases.py` | routes, DTOs, wiring |
| `TM/adapter/outbound/table/pyiceberg/commit_page_mapper.py`, `ListTableCommitsUseCaseOutput`, `list_table_commits.py`, `TableCommitApiResponse` | commit `schema_id` |
| `DS/components/DiffList/DiffList.tsx`, `DiffList.stories.tsx` (new), `DS/index.ts` | diff list |
| `FE/components/VersionList.tsx` (+ test), `FE/components/SchemaHistoryPanel.tsx`, `FE/components/PartitionSpecHistoryPanel.tsx`, `FE/components/tabs/useSchemaHistorySelection.ts`, `FE/lib/schemaChangeText.ts`, `FE/lib/partitionChangeText.ts`, `FE/lib/schemaDiffItems.ts`, `FE/lib/partitionDiffItems.ts` (new, with tests) | Schema tab pieces |
| `FE/components/tabs/SchemaTab.tsx` (+ new `SchemaTab.test.tsx`), `FE/components/tabs/CommitsTab.tsx`, `FE/pages/TablePage.tsx`, `FE/pages/TablePage.test.tsx`, `FE/pages/TablePage.stories.tsx`, `FE/stories/storyData.ts`, `FE/stories/lakehouseHandlers.ts` | tabs, stories (the last four on top of KCL-96's versions) |

Shorthands used in commands below:

- `PYTEST` = `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend pytest`
- `GATE` = `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`
- `GENAPI` = `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`

---

### Task 1: Schema fields keep their nested fields and ids

**Files:**
- Modify: `CAT/application/domain/model/shared/schema_field.py`, `CAT/application/domain/model/shared/schema.py`, `CAT/application/domain/model/shared/__init__.py`, `CAT/adapter/outbound/shared/polaris/iceberg_schema_from_polaris.py`
- Create: `CAT/application/domain/model/shared/schema_field_at_path.py`
- Test: `tests/context/catalog/application/domain/model/shared/test_schema.py`, `tests/context/catalog/adapter/outbound/table/polaris/test_tables_polaris_repo.py`

**Interfaces:**
- Produces:
  - `SchemaField.children: tuple[SchemaField, ...] = ()`: a struct's fields; a list's one child named `element` (id `element-id`, `required` = `element-required`); a map's `key` (id `key-id`, always required) and `value` (id `value-id`, `required` = `value-required`); each child's `type` is the same text `iceberg_type_from_polaris` renders and `doc` is the nested field's doc (None for element, key, value).
  - `SchemaField.outer_type -> str` (property): `struct`, `list` or `map` when `type` starts with `struct<`, `list<` or `map<`, else `type`.
  - `class SchemaFieldAtPath(ValueObject)`: `path: tuple[str, ...]`, `field: SchemaField`; property `depth -> int` = `len(path) - 1`. Exported from `CAT/application/domain/model/shared` and from `CAT/application/port/outbound/shared`.
  - `Schema.walk() -> tuple[SchemaFieldAtPath, ...]`: every field, depth-first pre-order (a field before its children, children in order).
- The view mapper shares `iceberg_schema_from_polaris`, so views get `children` too; the API's `SchemaFieldApiResponse` is unchanged. A schema built by `CreateTableService` keeps `children=()` (it only goes to Polaris).

- [ ] **Step 1: Write the failing tests**

```python
def test_walk_lists_nested_fields_after_their_parent():
    city = SchemaField(id=8, name="city", type="string", required=True, doc=None)
    shipping = SchemaField(id=7, name="shipping", type="struct<city: required string>", required=False, doc=None,
                           children=(city,))
    element = SchemaField(id=6, name="element", type="string", required=False, doc=None)
    tags = SchemaField(id=5, name="tags", type="list<string>", required=False, doc=None, children=(element,))
    walked = Schema(schema_id=1, fields=(tags, shipping)).walk()
    assert [(w.path, w.depth, w.field.id) for w in walked] == [
        (("tags",), 0, 5), (("tags", "element"), 1, 6), (("shipping",), 0, 7), (("shipping", "city"), 1, 8),
    ]

def test_outer_type_of_nested_and_primitive_fields(): ...  # "struct<a: int>"→"struct", "list<int>"→"list",
                                                          # "map<string, int>"→"map", "decimal(10,2)"→"decimal(10,2)"
```

In `test_tables_polaris_repo.py` (add a helper `_load_orders(body=None) -> Table` that does what the existing tests do inline: `PolarisStub()`, `stub.on("GET", ORDERS, httpx.Response(200, json=body or _load_result()))`, `TablesPolarisRepo(stub.client()).get(ORDERS_ID)`, asserting it is not None; there is no such helper at HEAD):

```python
def test_load_keeps_nested_field_ids():
    # fixture schema 1: tags (5) list element-id 6; shipping (7) struct with city (8)
    table = _load_orders()
    by_name = {f.name: f for f in table.current_schema.fields}
    assert [(c.id, c.name, c.type, c.required) for c in by_name["tags"].children] == [(6, "element", "string", False)]
    assert [(c.id, c.name, c.required) for c in by_name["shipping"].children] == [(8, "city", True)]

def test_load_keeps_map_key_and_value_ids(): ...  # a map field {key-id 11, value-id 12, value-required true}
                                                  # → children [(11, "key", True), (12, "value", True)]
                                                  # (the body is built as test_load_maps_map_types_and_optional_nested_elements
                                                  # builds its own, appending to schemas[1])
def test_nested_field_id_that_is_not_an_integer_is_unavailable(): ...  # element-id "6" → CatalogUnavailableError
```

- [ ] **Step 2: Run them and watch them fail**

Run: `PYTEST tests/context/catalog/application/domain/model/shared/test_schema.py tests/context/catalog/adapter/outbound/table/polaris/test_tables_polaris_repo.py -k "walk or outer_type or nested or map_key" -v`
Expected: FAIL, `SchemaField` has no field `children`.

- [ ] **Step 3: Implement** the fields, `walk()` and the mapper's `_children(iceberg_type)`, reading ids through `polaris_integer` (no coercion; a non-integer id is a TypeError, which `read_polaris_reply` turns into 502).

- [ ] **Step 4: Run them and watch them pass**, then the catalog suite: `PYTEST tests/context/catalog -q` and the architecture tests `PYTEST tests/architecture -q`.

- [ ] **Step 5: Commit** (`GATE scope=backend` passes) `feat(catalog): keep nested schema fields with their Iceberg ids (KCL-97)`

### Task 2: The table keeps every schema, every partition spec and each snapshot's schema id

**Files:**
- Modify: `CAT/application/domain/model/table/table.py`, `snapshot.py`, `partition_spec.py` (docstring: one spec, not "the default"), `CAT/adapter/outbound/table/polaris/table_from_polaris.py`, `snapshot_from_polaris.py`, `CAT/adapter/outbound/table/polaris/__init__.py`, `CAT/application/service/table/table_output_fields.py`, `CAT/application/port/inbound/table/get_table/output.py` (docstring), `CAT/adapter/inbound/web/table/dto.py` (`SnapshotApiResponse.schema_id`), every test or fake that builds a `Table` by keyword (`test_table.py`, `test_resolve_table_properties.py`, `test_table_property_services.py`, `test_table_services.py`, `test_tables_polaris_repo.py`, `test_table_routes.py` `_fields()`), `openapi.json` + generated client (`GENAPI`)
- Rename: `table_schema_from_polaris.py` → `table_schemas_from_polaris.py`, `partition_spec_from_polaris.py` → `partition_specs_from_polaris.py` (one function each, below)
- Test: `tests/context/catalog/application/domain/model/table/test_table.py`, `tests/context/catalog/adapter/outbound/table/polaris/test_tables_polaris_repo.py`, `tests/context/catalog/adapter/inbound/web/table/test_table_routes.py`

**Interfaces:**
- Consumes: Task 1 (`Schema.walk()`).
- Produces:
  - `Table` replaces the field `current_schema: Schema` with `schemas: tuple[Schema, ...]` and `current_schema_id: int`, and the field `partition_spec: PartitionSpec` with `partition_specs: tuple[PartitionSpec, ...]` and `default_spec_id: int`. `current_schema` and `partition_spec` stay as read-only properties returning the current schema and the default spec, so every reader is unchanged.
  - Invariant (`model_validator(mode="after")`, `InvariantViolation`): ids are unique and in ascending order in both tuples, and `current_schema_id` / `default_spec_id` name one of them.
  - `Table.define(...)` keeps its signature and builds `schemas=(schema,)`, `current_schema_id=schema.schema_id`, `partition_specs=(partition_spec,)`, `default_spec_id=partition_spec.spec_id`.
  - `Table.schema_by_id(schema_id: int) -> Schema | None`; `Table.previous_schema(schema_id: int) -> Schema | None` (the schema with the largest id below it); `Table.partition_spec_by_id(spec_id: int) -> PartitionSpec | None`; `Table.previous_partition_spec(spec_id: int) -> PartitionSpec | None`.
  - `Table.column_paths() -> dict[int, tuple[str, ...]]`: every field id of every schema to its path; the current schema's paths win, then higher schema ids over lower.
  - `Snapshot.schema_id: int | None = None`, read from `schema-id` (absent in v1 → None).
  - `table_schemas_from_polaris(metadata) -> tuple[tuple[Schema, ...], int]` (schemas sorted by id, current id); without `schemas` (v1) the single `schema` with `current_schema_id` = its `schema-id` or 0. `partition_specs_from_polaris(metadata) -> tuple[tuple[PartitionSpec, ...], int]`; without `default-spec-id` (v1) one spec 0 from `partition-spec` (empty when absent or null). A current or default id that matches nothing still raises ValueError.
  - Each output snapshot dict and `SnapshotApiResponse` gain `schema_id: int | None`.

- [ ] **Step 1: Write the failing tests**

```python
def test_load_keeps_every_schema_and_spec_and_snapshot_schema_ids():
    table = _load_orders()  # fixture: schemas 0 and 1, current 1; specs 0 and 1, default 1
    assert [s.schema_id for s in table.schemas] == [0, 1]
    assert table.current_schema_id == 1 and table.current_schema.schema_id == 1
    assert [len(s.fields) for s in table.schemas] == [3, 6]
    assert [s.spec_id for s in table.partition_specs] == [0, 1] and table.default_spec_id == 1
    assert [[f.field_id for f in s.fields] for s in table.partition_specs] == [[1000], [1000, 1001]]
    assert [(s.snapshot_id, s.schema_id) for s in table.snapshots] == [
        (8333017788700497002, 0), (3051729675574597004, 1),
    ]
```

Extend `test_v1_metadata_without_schemas_or_specs_uses_the_single_schema_and_spec`: one schema, one spec 0, snapshots' `schema_id` None. In `test_table.py`:

```python
def test_define_holds_one_schema_and_one_spec(): ...       # schemas == (schema,), current id == schema id
def test_duplicate_schema_ids_are_refused(): ...           # InvariantViolation
def test_current_schema_id_must_name_a_schema(): ...       # current 5 with schemas 0, 1 → InvariantViolation
def test_schemas_out_of_id_order_are_refused(): ...
def test_previous_schema_is_the_next_lower_id(): ...       # schemas 0,1,2: previous(2) is 1, previous(0) is None
def test_reused_schema_id_stays_current(): ...             # schemas 0,1,2, current 1: current_schema is 1
def test_column_paths_prefer_the_current_schema(): ...     # id 2 named "customer" in current 1, "customer_id" in 0
                                                           # → paths[2] == ("customer",); a field only in 0 keeps its path
```

Route test: `GET .../tables/orders` shows `snapshots[0]["schema_id"] == 0`.

- [ ] **Step 2: Run them and watch them fail**

Run: `PYTEST tests/context/catalog -k "schema or spec or define or column_paths" -v`
Expected: FAIL, `Table` has no field `schemas`.

- [ ] **Step 3: Implement**, update the keyword constructions in tests and fakes, then `GENAPI`.

- [ ] **Step 4: Run them and watch them pass**: `PYTEST tests/context/catalog -q`; `GATE scope=all` (includes the contract test that `openapi.json` and the generated client match).

- [ ] **Step 5: Commit** `feat(catalog): keep every schema, partition spec and snapshot schema id of a table (KCL-97)`

### Task 3: Compare two schemas by field id

**Files:**
- Create: `CAT/application/domain/model/table/schema_change.py`, `schema_field_comparison.py`, `schema_comparison.py`; `CAT/application/domain/service/table/compare_schemas.py`; export them from the two `__init__.py`
- Test: `tests/context/catalog/application/domain/service/table/test_compare_schemas.py`

**Interfaces:**
- Consumes: Task 1 (`Schema.walk()`, `SchemaField.outer_type`).
- Produces:
  - `class SchemaChange(StrEnum)`: `ADDED = "added"`, `REMOVED = "removed"`, `RENAMED = "renamed"`, `TYPE_CHANGED = "type_changed"`, `NULLABILITY_CHANGED = "nullability_changed"`, `DOC_CHANGED = "doc_changed"` (in this order).
  - `class SchemaFieldComparison(ValueObject)`: `field_id: int`, `depth: int`, `path: tuple[str, ...] | None`, `previous_path: tuple[str, ...] | None`, `type: str | None`, `previous_type: str | None`, `required: bool | None`, `previous_required: bool | None`, `doc: str | None`, `previous_doc: str | None`, `changes: tuple[SchemaChange, ...]` (in enum order). The current side is None for a removed field, the previous side None for an added one; `type` is `outer_type`; `depth` is the depth in the newer schema, or in the base for a removed field.
  - `class SchemaComparison(ValueObject)`: `base_schema_id: int | None`, `schema_id: int`, `fields: tuple[SchemaFieldComparison, ...]`; `change_counts() -> dict[SchemaChange, int]` (every kind, zeros included: the number of fields carrying it).
  - `compare_schemas(base: Schema | None, schema: Schema) -> SchemaComparison`. `base=None` (no earlier version): every field unchanged, `previous_*` equal to the current values, `base_schema_id` None. Order: the newer schema's walk order, each removed field placed right after the nearest field before it in the base's walk order that is in the list (first if none), removed fields kept in base order.

- [ ] **Step 1: Write the failing tests** (schemas built with `SchemaField(...)`; `_cmp(base, schema)` returns `{f.field_id: f for f in compare_schemas(base, schema).fields}`)

```python
def test_added_and_removed_fields(): ...            # id 4 only in new → (ADDED,), id 3 only in base → (REMOVED,),
                                                    # removed row: path None, previous_path ("order_ts",)
def test_rename_is_matched_by_id():
    rows = _cmp(schema(field(2, "customer_id", "long")), schema(field(2, "customer", "long")))
    assert rows[2].changes == (SchemaChange.RENAMED,)
    assert (rows[2].previous_path, rows[2].path) == (("customer_id",), ("customer",))

def test_rename_and_promotion_are_one_row():
    rows = _cmp(schema(field(2, "customer_id", "int")), schema(field(2, "customer", "long")))
    assert list(rows) == [2]
    assert rows[2].changes == (SchemaChange.RENAMED, SchemaChange.TYPE_CHANGED)

def test_nullability_and_doc_changes(): ...         # required True→False, doc None→"Primary key"
def test_nested_child_added_shows_full_path(): ...  # shipping struct gains zip (9) → path ("shipping","zip"), depth 1;
                                                    # shipping itself unchanged
def test_parent_rename_does_not_rename_children(): ...  # shipping→ship_to: row 7 RENAMED; row 8 changes () with
                                                        # path ("ship_to","city"), previous_path ("shipping","city")
def test_list_element_promotion(): ...              # tags list<int>→list<long>: row 6 path ("tags","element")
                                                    # TYPE_CHANGED; row 5 (type "list") unchanged
def test_removed_field_sits_after_its_former_neighbour(): ...  # base a(1) b(2) c(3), new a(1) c(3) → order [1, 2, 3]
def test_removed_first_field_comes_first(): ...     # base a(1) b(2), new b(2) → order [1, 2]
def test_no_base_lists_every_field_unchanged(): ... # base_schema_id None, every changes == ()
def test_change_counts_cover_every_kind():
    comparison = compare_schemas(schema(field(1, "a", "int")), schema(field(1, "b", "long"), field(2, "c", "int")))
    assert comparison.change_counts() == {
        SchemaChange.ADDED: 1, SchemaChange.REMOVED: 0, SchemaChange.RENAMED: 1,
        SchemaChange.TYPE_CHANGED: 1, SchemaChange.NULLABILITY_CHANGED: 0, SchemaChange.DOC_CHANGED: 0,
    }
```

- [ ] **Step 2: Run them and watch them fail**

Run: `PYTEST tests/context/catalog/application/domain/service/table/test_compare_schemas.py -v`
Expected: FAIL, `compare_schemas` not importable.

- [ ] **Step 3: Implement** `compare_schemas` with two `walk()` passes indexed by field id.

- [ ] **Step 4: Run them and watch them pass**; `PYTEST tests/architecture -q` (domain purity, one object per file).

- [ ] **Step 5: Commit** (`GATE scope=backend`) `feat(catalog): compare two schemas by field id (KCL-97)`

### Task 4: Compare two partition specs

**Files:**
- Create: `CAT/application/domain/model/table/partition_change.py`, `partition_field_comparison.py`, `partition_spec_comparison.py`; `CAT/application/domain/service/table/compare_partition_specs.py`; exports
- Test: `tests/context/catalog/application/domain/service/table/test_compare_partition_specs.py`

**Interfaces:**
- Consumes: Task 2 (`Table.column_paths()` supplies the mapping).
- Produces:
  - `class PartitionChange(StrEnum)`: `ADDED = "added"`, `REMOVED = "removed"`, `RENAMED = "renamed"`, `TRANSFORM_CHANGED = "transform_changed"`.
  - `class PartitionFieldComparison(ValueObject)`: `field_id: int | None`, `previous_field_id: int | None`, `name: str | None`, `previous_name: str | None`, `source_path: tuple[str, ...] | None`, `previous_source_path: tuple[str, ...] | None`, `transform: str | None`, `previous_transform: str | None`, `changes: tuple[PartitionChange, ...]`; methods `expression() -> str | None` and `previous_expression() -> str | None` returning `f"{transform}({'.'.join(source_path)})"`.
  - `class PartitionSpecComparison(ValueObject)`: `base_spec_id: int | None`, `spec_id: int`, `fields: tuple[PartitionFieldComparison, ...]`; `change_counts() -> dict[PartitionChange, int]`; `field_count() -> int` (fields of the newer spec that are not `void`).
  - `compare_partition_specs(base: PartitionSpec | None, spec: PartitionSpec, column_paths: Mapping[int, tuple[str, ...]]) -> PartitionSpecComparison`. A source id missing from `column_paths` has path `(f"#{source_id}",)`. Order: the newer spec's fields, then unpaired removed fields in base order.

- [ ] **Step 1: Write the failing tests** (`PATHS = {2: ("customer_id",), 3: ("order_ts",)}`)

```python
def test_added_bucket_field(): ...      # spec 0 {1000 day(3)} → spec 1 {1000, 1001 bucket[16](2)}: row 1001 (ADDED,),
                                        # expression "bucket[16](customer_id)"; row 1000 unchanged
def test_day_to_hour_is_one_transform_change():
    base = spec(0, pfield(1000, "order_ts_day", "day", 3))
    new = spec(1, pfield(1001, "order_ts_hour", "hour", 3))
    (row,) = compare_partition_specs(base, new, PATHS).fields
    assert (row.field_id, row.previous_field_id) == (1001, 1000)
    assert row.changes == (PartitionChange.RENAMED, PartitionChange.TRANSFORM_CHANGED)
    assert (row.previous_expression(), row.expression()) == ("day(order_ts)", "hour(order_ts)")

def test_renamed_field_keeps_its_id(): ...       # 1000 name a→b, same transform → (RENAMED,)
def test_v1_void_counts_as_removed(): ...        # 1000 day → 1000 void: (REMOVED,), expression() None,
                                                 # previous_expression() "day(order_ts)"
def test_void_in_both_versions_is_left_out(): ...
def test_unknown_source_column_reads_as_its_id(): ...  # source 7 → "identity(#7)"
def test_no_base_lists_every_field_unchanged(): ...    # base_spec_id None
def test_unpartitioned_to_partitioned(): ...     # spec 0 () → spec 1 {1000}: one ADDED row; field_count() == 1
```

- [ ] **Step 2: Run them and watch them fail**: `PYTEST tests/context/catalog/application/domain/service/table/test_compare_partition_specs.py -v`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run them and watch them pass**; `PYTEST tests/architecture -q`
- [ ] **Step 5: Commit** (`GATE scope=backend`) `feat(catalog): compare two partition specs, pairing transform changes by source column (KCL-97)`

### Task 5: Serve the version lists and comparisons

**Files:**
- Create: `CAT/application/port/inbound/table/list_table_schema_versions/{__init__,input,output,use_case}.py`, `.../get_table_schema_comparison/…`, `.../list_table_partition_spec_versions/…`, `.../get_table_partition_spec_comparison/…`; `CAT/application/service/table/list_table_schema_versions.py`, `get_table_schema_comparison.py`, `list_table_partition_spec_versions.py`, `get_table_partition_spec_comparison.py`, `load_table.py`
- Modify: both table `__init__.py` files (ports and services), `CAT/application/service/table/get_table.py` (use `load_table`), `CAT/application/service/table/load_table_and_catalog.py` (its table half calls `load_table`; it raises the same text today), `tests/architecture/test_service_structure.py` (add `load_table.py` to the helper allowlist, beside `load_table_and_catalog.py`), `CAT/adapter/inbound/web/table/router.py`, `dto.py`, `CAT/adapter/inbound/web/shared/web_use_cases.py`, `bootstrap/container/build_catalog_web_use_cases.py` (`tests/context/catalog/adapter/inbound/web/web_test_support.build_app` derives its stubs from `WebUseCases`, so it needs no change; `tests/bootstrap/container/test_build_catalog_web_use_cases.py` asserts the four new services are wired), `src/data-platform/backend/CLAUDE.md` (on top of KCL-96's version) (one paragraph beside the table-properties one: what the comparisons match on and the four routes), `openapi.json` + generated client
- Test: `tests/context/catalog/application/service/table/test_table_version_services.py` (new), `tests/context/catalog/adapter/inbound/web/table/test_table_version_routes.py` (new)

**Interfaces:**
- Consumes: Tasks 2 to 4.
- Produces:
  - `load_table(tables_repo: TablesRepo, table_id: TableId) -> Table`, raising `NotFoundError("table orders not found in namespace ['inventory'] of catalog iceberg")` (GetTableService's current text).
  - Every input: `catalog: str`, `namespace: tuple[str, ...]`, `name: str`; the comparisons add `schema_id: int, base_schema_id: int | None = None` / `spec_id: int, base_spec_id: int | None = None`.
  - `ListTableSchemaVersionsUseCaseOutput`: `current_schema_id: int`, `items: tuple[Version, ...]` newest id first; nested `Version`: `schema_id: int`, `previous_schema_id: int | None`, `current: bool`, `column_count: int` (top-level fields), `changes: dict[str, int] | None` (`change_counts()` keyed by the enum values against `previous_schema`; None for the first version).
  - `GetTableSchemaComparisonUseCaseOutput`: `base_schema_id: int | None`, `schema_id: int`, `items: tuple[Field, ...]`; nested `Field` with `SchemaFieldComparison`'s fields as primitives (`changes: tuple[str, ...]`). Base = `base_schema_id` when given, else `previous_schema(schema_id)` (None for the first version). Unknown `schema_id` → `NotFoundError("schema 9 not found in table orders")`, unknown base the same with its id; base equal to schema is allowed (all unchanged).
  - `ListTablePartitionSpecVersionsUseCaseOutput`: `default_spec_id: int`, `items: tuple[Version, ...]`; `Version`: `spec_id`, `previous_spec_id: int | None`, `default: bool`, `field_count: int`, `changes: dict[str, int] | None`.
  - `GetTablePartitionSpecComparisonUseCaseOutput`: `base_spec_id: int | None`, `spec_id: int`, `items: tuple[Field, ...]`; `Field` = `PartitionFieldComparison`'s fields plus `expression: str | None`, `previous_expression: str | None`. Unknown → `NotFoundError("partition spec 4 not found in table orders")`.
  - Routes on the catalog table router (route `name=` is the operation id, so the hooks are `useListCatalogTableSchemaVersions`, `useGetCatalogTableSchemaComparison`, `useListCatalogTablePartitionSpecVersions`, `useGetCatalogTablePartitionSpecComparison`):
    - `GET /{table}/schema-versions`, name `list_catalog_table_schema_versions` → `CatalogTableSchemaVersionsApiResponse {current_schema_id: int, versions: list[CatalogTableSchemaVersionApiResponse]}`; a version is `{schema_id, previous_schema_id, current, column_count, changes: SchemaChangeCountsApiResponse | None}`; counts `{added, removed, renamed, type_changed, nullability_changed, doc_changed}`, all `int`.
    - `GET /{table}/schema-versions/{schema_id}/comparison`, query `base: int | None`, name `get_catalog_table_schema_comparison` → `CatalogTableSchemaComparisonApiResponse {base_schema_id, schema_id, fields: list[SchemaFieldComparisonApiResponse]}`; a field has the port fields with `path` / `previous_path` as `list[str] | None` and `changes: list[Literal["added", "removed", "renamed", "type_changed", "nullability_changed", "doc_changed"]]`.
    - `GET /{table}/partition-spec-versions`, name `list_catalog_table_partition_spec_versions` → `CatalogTablePartitionSpecVersionsApiResponse {default_spec_id, versions: [{spec_id, previous_spec_id, default, field_count, changes: PartitionChangeCountsApiResponse | None}]}`; counts `{added, removed, renamed, transform_changed}`.
    - `GET /{table}/partition-spec-versions/{spec_id}/comparison`, query `base`, name `get_catalog_table_partition_spec_comparison` → `CatalogTablePartitionSpecComparisonApiResponse {base_spec_id, spec_id, fields: list[PartitionFieldComparisonApiResponse]}`; `changes: list[Literal["added", "removed", "renamed", "transform_changed"]]`.
  - DTO docstrings are the published descriptions; write each as one sentence saying what it holds (they reach the console's generated client).

- [ ] **Step 1: Write the failing tests** (services on `InMemoryTablesRepo` holding the Task 2 fixture shape: schemas 0 and 1, specs 0 and 1)

```python
def test_schema_versions_newest_first_with_counts(tables_repo):
    out = ListTableSchemaVersionsService(tables_repo).execute(_input())
    assert out.current_schema_id == 1
    assert [(v.schema_id, v.previous_schema_id, v.current, v.column_count) for v in out.items] == [
        (1, 0, True, 6), (0, None, False, 3),
    ]
    assert out.items[0].changes == {"added": 5, "removed": 0, "renamed": 0, "type_changed": 0,
                                    "nullability_changed": 0, "doc_changed": 1}
    assert out.items[1].changes is None

def test_schema_comparison_defaults_to_the_previous_version(): ...  # schema_id 1 → base_schema_id 0
def test_schema_comparison_with_a_chosen_base(): ...                # schema_id 0, base 1 → fields 4..8 REMOVED
def test_first_schema_has_no_base(): ...                            # schema_id 0 → base None, all unchanged
def test_unknown_schema_or_base_is_not_found(): ...                 # 9 → NotFoundError "schema 9 not found in table orders"
def test_partition_spec_versions_mark_the_default(): ...            # [(1, 0, True, 2), (0, None, False, 1)],
                                                                    # items[0].changes["added"] == 1
def test_partition_comparison_carries_expressions(): ...            # row 1001 expression "bucket[16](customer_id)"
def test_unknown_table_is_not_found(): ...                          # all four services
```

Routes (stub use cases, as `test_table_routes.py` does): each route answers 200 with the documented body; `?base=0` reaches the input as `base_schema_id=0`; no `base` → None; `?base=x` → 422; a `NotFoundError` → 404 with its message; the namespace splits on U+001F.

- [ ] **Step 2: Run them and watch them fail**: `PYTEST tests/context/catalog/application/service/table/test_table_version_services.py tests/context/catalog/adapter/inbound/web/table/test_table_version_routes.py -v`
- [ ] **Step 3: Implement**, wire the four services in `build_catalog_web_use_cases.py`, update `src/data-platform/backend/CLAUDE.md`, then `GENAPI`.
- [ ] **Step 4: Run them and watch them pass**; `PYTEST -q`; `GATE scope=all`
- [ ] **Step 5: Commit** `feat(catalog): list a table's schema and partition spec versions and compare any two (KCL-97)`

### Task 6: Each commit carries its schema id

**Files:**
- Modify: `TM/adapter/outbound/table/pyiceberg/commit_page_mapper.py` (`"schema_id": snapshot.schema_id` in the dict beside `"snapshot_id"`, `"parent_id"`, `"committed_at"`, `"operation"`, `"summary"`, `"writer"`), `TM/application/port/outbound/table/read_table_metadata/table_commit_page.py` (docstring lists `schema_id`), `TM/application/port/inbound/table/list_table_commits/output.py` (`Commit.schema_id: int | None`), `TM/application/service/table/list_table_commits.py` (`commit.get("schema_id")`, so a fake or older page without the key reads None; the other keys stay `commit[...]`), `TM/adapter/inbound/web/table/dto.py` (KCL-96's version; `TableCommitApiResponse.schema_id: int | None`), `openapi.json` + generated client
- Test: `tests/context/table_maintenance/adapter/outbound/table/pyiceberg/test_read_table_metadata_pyiceberg_gateway.py` (KCL-96's version), `tests/context/table_maintenance/application/service/table/test_list_table_commits.py`, `tests/context/table_maintenance/adapter/inbound/web/table/test_table_commits_route.py`

**Interfaces:**
- Produces: `GET /v1/tables/{table_uuid}/commits` items gain `schema_id: int | None` (the TypeScript `TableCommitApiResponse.schema_id: number | null`).

- [ ] **Step 1: Failing tests:** on the `SqlCatalog` fixture, append, evolve the schema (`update_schema().add_column(...)`), append again: `list_commits` gives the newer commit `schema_id == 1` and the older `0`; the service maps `schema_id` and a commit dict without the key reads None; the route body carries `"schema_id": 1`.
- [ ] **Step 2: Run and watch them fail**: `PYTEST tests/context/table_maintenance -k "commit" -v`
- [ ] **Step 3: Implement**, then `GENAPI`.
- [ ] **Step 4: Run and watch them pass**; `GATE scope=all`
- [ ] **Step 5: Commit** `feat(table-maintenance): say which schema version each commit was written with (KCL-97)`

### Task 7: The design system's `DiffList`

**Files:**
- Create: `DS/components/DiffList/DiffList.tsx`, `DS/components/DiffList/DiffList.stories.tsx`
- Modify: `DS/index.ts` (export `DiffList`, `type DiffListProps`, `type DiffListItem`, `type DiffChange`), `src/design-system/CLAUDE.md` (add `DiffList` to the plain-name list and one line: rows say their change in text and neutral badges, never status colours)

**Interfaces:**
- Produces:

```ts
export type DiffChange = "added" | "removed" | "changed" | "unchanged";
export type DiffListItem = {
  id: string;
  change: DiffChange;
  label: ReactNode;         // what the row is, e.g. a field path
  depth?: number;           // nesting level, indents the row (default 0)
  tags?: string[];          // what changed on a "changed" row, e.g. ["Renamed", "Type changed"]
  before?: ReactNode;       // the old value (removed rows, and changed rows whose value changed)
  after?: ReactNode;        // the new value (every row but removed)
  description?: ReactNode;  // a second line, e.g. "Renamed from customer_id" or the field's doc
};
export type DiffListProps = {
  caption: string;                                    // accessible name of the list
  items: DiffListItem[];
  onlyChanges: boolean;
  onOnlyChangesChange: (onlyChanges: boolean) => void;
  onlyChangesLabel?: string;                          // default "Show changes only"
  emptyState?: ReactNode;                             // no items; default "Nothing to compare."
  noChangesState?: ReactNode;                         // only changes on, none changed; default "No changes."
};
```

- Rendering: a header row with the design system's `Switch` (`onlyChangesLabel`) and a count, `3 changes` / `1 change` / `No changes`; then a `<ul aria-label={caption}>` of `<li>` rows: an `aria-hidden` sign (`+` added, `−` removed, `~` changed, none unchanged), the label in `type-code`, a neutral `Badge` "Added" or "Removed", or one `Badge` per tag on a changed row; the value as `before → after` when both are given (the arrow `aria-hidden`, followed by visually hidden text "changed to"), else the one given; the description below in `text-on-surface-variant`. A removed row's label is `line-through text-on-surface-variant`. Indent `depth × 1rem` with `padding-inline-start`. Values `break-all`. Rows use the density utilities (`min-h-row`). No status colours, no `--sd-*`.

- [ ] **Step 1: Write the stories first**, each with axe on:
  - `Default` (a mixed schema-like list: two unchanged, one added, one removed, one changed with `["Renamed", "Type changed"]`, one nested child at depth 1). Play: Tab lands on the switch with a visible focus ring (`expectFocusRing`); Space turns it on and the two unchanged rows leave the list (`getAllByRole("listitem")` length 4) and the count still reads `4 changes`; Enter turns it off and they return; `onOnlyChangesChange` called with `true` then `false`.
  - `OnlyChanges` (starts on), `NoChanges` (on, every item unchanged → "No changes."), `Empty` (no items → "Nothing to compare."), `TransformChange` (one changed row `day(order_ts) → hour(order_ts)`; asserts the row's text contains "changed to"), `Phone` (`globals: PHONE`-style viewport, a 120-character path; `expectNoHorizontalPageScroll`), `Dense` (desktop viewport; records the expanded row height as a departure: Serendie has no diff list).
- [ ] **Step 2: Run and watch them fail**: `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/design-system run test:stories -- DiffList`
- [ ] **Step 3: Implement** `DiffList.tsx` (the story wraps it in local state so the switch works).
- [ ] **Step 4: Run and watch them pass**; `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/design-system run lint`, `run typecheck`; `GATE scope=frontend`
- [ ] **Step 5: Commit** `feat(design-system): add DiffList for comparing two versions (KCL-97)`

### Task 8: The Schema tab lists and compares versions

**Files:**
- Create: `FE/lib/schemaChangeText.ts`, `FE/lib/partitionChangeText.ts`, `FE/lib/schemaDiffItems.ts`, `FE/lib/partitionDiffItems.ts` (each with a `.test.ts`), `FE/components/VersionList.tsx` (+ `.test.tsx`), `FE/components/SchemaHistoryPanel.tsx`, `FE/components/PartitionSpecHistoryPanel.tsx`, `FE/components/tabs/useSchemaHistorySelection.ts`, `FE/components/tabs/SchemaTab.test.tsx`
- Modify: `FE/components/tabs/SchemaTab.tsx` (its `<SchemaFieldsPanel schema={table.schema} />` becomes `SchemaHistoryPanel`, and its "Partition spec" `Panel` with the partition `DataTable` becomes `PartitionSpecHistoryPanel`; `SchemaFieldsPanel` itself stays, `ViewPage` uses it), and on top of KCL-96's versions: `FE/stories/storyData.ts`, `FE/stories/lakehouseHandlers.ts` (the four generated `…MockHandler`s from `@/api/generated/tables/tables.msw`, where both contexts' `tables` tag lands, in `lakehouseHandlers()`'s list), `FE/pages/TablePage.stories.tsx`, `FE/pages/TablePage.test.tsx` (`stubTable` gains `GET ${TABLE}/schema-versions*` and `GET ${TABLE}/partition-spec-versions*`, answering version lists and comparisons written for `catalogTableFixture()`'s `address` struct and `placed_at_day` field; the test "shows the schema with partition spec sort order and spark ddl" now finds the current version's `Current` badge and an `address.zip` row in the "Schema" region (a comparison row shows the outer type `struct`, no longer `struct<city: required string, zip: string>`), the `Default` badge and `day(placed_at)` in the "Partition spec" region, and keeps its Sort order and DDL assertions), `src/data-platform/frontend/CLAUDE.md` (Catalog pages: one bullet on the Schema tab, after KCL-96's change to "The table page joins two APIs")
- Test: the files above

**Interfaces:**
- Consumes: Task 5's generated hooks and types; Task 7's `DiffList`.
- Produces:
  - `schemaChangeSummary(changes: SchemaChangeCountsApiResponse | null): string`: null → `"First version"`; all zero → `"No changes"`; else the non-zero kinds in enum order joined by `" · "`: `+N added`, `−N removed`, `N renamed`, `N type changed`, `N nullability changed`, `N doc changed`. `partitionChangeSummary(changes: PartitionChangeCountsApiResponse | null): string` the same with `N transform changed`. `schemaChangeTag(change)` / `partitionChangeTag(change)`: `"Renamed"`, `"Type changed"`, `"Nullability changed"`, `"Doc changed"`, `"Transform changed"`.
  - `schemaDiffItems(comparison: CatalogTableSchemaComparisonApiResponse): DiffListItem[]`: `id` = field id; `change` = `added` / `removed` when listed, `changed` when other changes, else `unchanged`; `label` = `(path ?? previous_path).join(".")`; `depth`; `after` = `` `${type} · ${required ? "required" : "optional"}` `` (absent when removed), `before` the same of the previous side when removed or when type or nullability changed; `description` = `Renamed from <previous path>` when renamed, `Doc: <previous or "none"> → <doc or "none">` when the doc changed (joined `" · "`), else the doc when there is one. `partitionDiffItems(...)`: `id` = `field_id ?? previous_field_id`, `label` = `name ?? previous_name`, `after` = `expression`, `before` = `previous_expression` when removed or transform changed, `description` = `Renamed from <previous_name>` when renamed.
  - `VersionList({ label, versions, selectedId, onSelect, visibleCount = 10 })`, `versions: { id: number; title: string; description: string; badge?: string }[]` newest first: the design system's `List` / `ListItem` (`isSelected`, `onSelect`, `trailingItem` = neutral `Badge` with `badge`); only the first `visibleCount` shown, then a ghost `Button` "Show N earlier versions" that shows the rest; it starts expanded when `selectedId` is among the hidden ones.
  - `useSchemaHistorySelection()` → `{ schemaId, baseSchemaId, schemaOnlyChanges, specId, baseSpecId, specOnlyChanges, setSchema(id), setBaseSchema(id | undefined), setSchemaOnlyChanges(on), setSpec(id), setBaseSpec(id | undefined), setSpecOnlyChanges(on) }` over the url params `schema`, `base`, `only_changes=1`, `spec`, `spec_base`, `spec_only_changes=1`; a value that is not a non-negative integer reads as undefined; writes use `replace` and drop a param set to its default; choosing a new version clears its `base`.
  - `SchemaHistoryPanel({ table })` (Panel "Schema"): loads `useListCatalogTableSchemaVersions`; the selected id is the url's `schema` when the list has it, else `current_schema_id` (with the "not in this table's history" line when the url named another); a `Select` "Compare with" whose items are `previous` ("Previous version (vN)", or "No earlier version" for the first) and every other version `vN`; then `useGetCatalogTableSchemaComparison(catalog, apiNamespace(parts), name, selected, { base })` into `DiffList` (caption `Changes in schema vN`). `PartitionSpecHistoryPanel({ table })` (Panel "Partition spec") the same with `default_spec_id`, badge `Default`, `emptyState` "Unpartitioned.", caption `Changes in partition spec vN`. Both: version list beside the comparison from 768px (`md:flex-row`, list `md:w-64 md:shrink-0`), above it below; loading `PanelSkeleton`, errors a negative `Banner` "Could not load schema versions: …".
  - `SchemaTab`: `SchemaHistoryPanel`, `PartitionSpecHistoryPanel`, the unchanged Sort order panel, and the DDL panel titled "DDL (Spark SQL)" with the line "Built from the current schema (vN); earlier versions have no DDL here." above the code.

- [ ] **Step 1: Write the failing tests and stories**

```ts
it("summarises a version's changes", () => {
  expect(schemaChangeSummary({ added: 1, removed: 0, renamed: 0, type_changed: 1, nullability_changed: 0, doc_changed: 0 }))
    .toBe("+1 added · 1 type changed");
  expect(schemaChangeSummary(null)).toBe("First version");
  expect(partitionChangeSummary({ added: 0, removed: 0, renamed: 0, transform_changed: 0 })).toBe("No changes");
});
```

`schemaDiffItems`: a renamed and promoted field gives `{ change: "changed", tags: ["Renamed", "Type changed"], before: "int · optional", after: "long · optional", description: "Renamed from customer_id" }`; a removed nested field has label `shipping.zip` and no `after`. `VersionList`: 12 versions show 10 and "Show 2 earlier versions"; a selected 12th starts expanded; keyboard: Tab to the first version, Enter calls `onSelect`, Tab reaches the button and Enter reveals the rest. `SchemaTab.test.tsx` (MSW through `stubCatalogApi` / generated handlers, `MemoryRouter` with a location probe):
  - opens on the current version: `v1` carries `Current` and "+5 added · 1 doc changed", the comparison request has no `base`;
  - choosing `v0` puts `?schema=0` in the url and requests the comparison of 0;
  - "Compare with" `v1` while on `v0` puts `&base=1` and requests `?base=1`;
  - the switch puts `only_changes=1` and hides unchanged rows;
  - current schema 1 of schemas 0, 1, 2 (reused id): `Current` on `v1`, opens on `v1`;
  - `?schema=9` and `?schema=abc`: opens on the current version, shows "Schema v9 is not in this table's history; showing the current schema (v1)." (no line for `abc`), and no comparison request for 9;
  - the partition panel shows `Default` on `v1` and a transform change row reading `day(order_ts)` → `hour(order_ts)`; an unpartitioned table reads "Unpartitioned.";
  - the DDL panel says it is built from the current schema.

Stories in `TablePage.stories.tsx` (fixtures in `storyData.ts`, handlers in `lakehouseHandlers.ts` answering each comparison by its `schema_id` and `base`): update `Schema` (finds `Current` and `+5 added · 1 doc changed`), add `SchemaCompareTwoVersions` (route `${ORDERS}/schema?schema=0&base=1`), `SchemaOnlyChanges`, `SchemaManyVersions` (12 versions, "Show 2 earlier versions"), `SchemaPartitionTransformChange`, `SchemaVersionsError` (`apiError` on the versions route), `SchemaPhone` (`globals: PHONE`, `expectNoHorizontalPageScroll`).

- [ ] **Step 2: Run and watch them fail**: `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend test -- --run schemaChangeText partitionChangeText schemaDiffItems partitionDiffItems VersionList SchemaTab TablePage`, then `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories -- TablePage`
- [ ] **Step 3: Implement** with design-system components only (`List`, `ListItem`, `Badge`, `Button`, `Select`, `Panel`, `Banner`, `DiffList`), semantic utilities only, identifiers in `type-code`.
- [ ] **Step 4: Run and watch them pass**; `GATE scope=frontend`
- [ ] **Step 5: Commit** `feat(console): list and compare schema and partition spec versions on the Schema tab (KCL-97)`

### Task 9: The Commits tab links each commit to its schema version

**Files:**
- Modify: `FE/components/tabs/CommitsTab.tsx`, `FE/components/tabs/CommitsTab.test.tsx`, `FE/pages/TablePage.tsx`, and on top of KCL-96's and Task 8's versions `FE/pages/TablePage.stories.tsx` and `FE/stories/storyData.ts` (`schema_id` on each item of `COMMITS`)

**Interfaces:**
- Consumes: Task 6 (`TableCommitApiResponse.schema_id`), Task 8's `schema` url param.
- Produces: `CommitsTab({ tableUuid, schemaHref }: { tableUuid: string; schemaHref: (schemaId: number) => string })` (today `CommitsTab({ tableUuid })`, which hands `tableUuid` to `CommitHistory`; `schemaHref` goes down `CommitHistory` → `CommitDaySection` → `CommitRow`). `TablePage`'s `tabBody` (case `"commits"`, inside its `MaintenanceGate`) passes `` (id) => `${tablePath(table.catalog, table.namespace, table.name, "schema")}?schema=${id}` `` (`tablePath` from `@/lib/catalogPaths`). Each `CommitRow` with a `schema_id` shows, before the short snapshot id, a `TextLink` wrapping the router `Link` with text `v<N>`, accessible name `Schema v<N>` and a `Tooltip` "Written with schema v<N>"; a commit with no `schema_id` shows nothing there.

- [ ] **Step 1: Failing tests and stories:** `CommitsTab.test.tsx`: a commit with `schema_id: 1` has a link named `Schema v1` whose href is `schemaHref(1)`; a commit with `schema_id: null` has no schema link. Story `CommitsSchemaLink` (route `${ORDERS}/commits`): click `Schema v0` and land on the Schema tab with `v0` selected (its list item `aria-current` / selected state and the comparison caption `Changes in schema v0`). `CommitsPhone` still passes `expectNoHorizontalPageScroll`.
- [ ] **Step 2: Run and watch them fail**: `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend test -- --run CommitsTab`
- [ ] **Step 3: Implement**
- [ ] **Step 4: Run and watch them pass**; `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories -- TablePage`; `GATE scope=frontend`
- [ ] **Step 5: Commit** `feat(console): link each commit to the schema version it was written with (KCL-97)`

### Task 10: Verify on a rebuilt cluster (run by the controller)

**Batched (refreshed 2026-11-20):** the controller runs this task in one batch rebuild with KCL-91 (Task 9 of `docs/superpowers/plans/2026-11-20-maintenance-policy-target-state.md`) and KCL-96 (Task 11 of `docs/superpowers/plans/2026-11-20-overview-metric-trends.md`), after both plans here are implemented: Step 1 is done once for the three, then each plan's checks run on that cluster. The checks below stay as they are; API calls through the gateway use `gateway::curl` (Global Constraints, "Cluster access").

- [ ] **Step 1:** `task -d /Users/kcl/Projects/retail-lakehouse offboard KUBE_CONTEXT=retail-lakehouse`, then `task -d /Users/kcl/Projects/retail-lakehouse onboard KUBE_CONTEXT=retail-lakehouse`; `task -d /Users/kcl/Projects/retail-lakehouse apps:validate KUBE_CONTEXT=retail-lakehouse` exits 0.
- [ ] **Step 2:** Open the gateway: `kubectl port-forward service/platform-gateway-istio 8591:80 --namespace istio-ingress --context retail-lakehouse`. Create `iceberg.inventory.schema_demo` with `gateway::curl /api/v1/catalogs/iceberg/namespaces/inventory/tables -fsS -X POST -H 'Content-Type: application/json' --data '<body>'`, body `{"name": "schema_demo", "schema_fields": [{"name": "order_id", "type": "int"}, {"name": "customer_id", "type": "long", "required": false}, {"name": "order_ts", "type": "timestamptz", "required": false}, {"name": "shipping", "type": "struct<city: string>", "required": false}], "partition_fields": [{"source_column": "order_ts", "transform": "day"}]}`.
- [ ] **Step 3:** Evolve it from the API pod, appending one row after each change so each version has a commit:

```bash
kubectl exec deployment/table-maintenance-api --namespace lakehouse-control-plane --context retail-lakehouse -- python -c '
import datetime, pyarrow as pa
from pyiceberg.transforms import HourTransform
from pyiceberg.types import LongType, StringType
from bootstrap.configs import AppSettings
from bootstrap.container import build_catalog_factory
catalog = build_catalog_factory(AppSettings().catalog)("iceberg")
def append():
    t = catalog.load_table(("inventory", "schema_demo"))
    t.append(pa.Table.from_pylist([{"order_id": 1, "order_ts": datetime.datetime.now(datetime.UTC)}], schema=t.schema().as_arrow()))
append()
t = catalog.load_table(("inventory", "schema_demo"))
with t.update_schema() as u:
    u.rename_column("customer_id", "customer")
    u.update_column("order_id", field_type=LongType(), required=False)
    u.add_column(("shipping", "zip"), StringType())
append()
t = catalog.load_table(("inventory", "schema_demo"))
with t.update_spec() as s:
    s.remove_field("order_ts_day"); s.add_field("order_ts", HourTransform(), "order_ts_hour")
append()
'
```

  If the API pod cannot reach object storage, run the same command in `deployment/table-maintenance-worker`.
- [ ] **Step 4: API checks** (`gateway::curl /api/v1/catalogs/iceberg/namespaces/inventory/tables/schema_demo/... -fsS`):
  - `schema-versions`: `current_schema_id` 1, versions `[1, 0]`, `v1` changes `added 1, renamed 1, type_changed 1, nullability_changed 1`, `v0` changes null.
  - `schema-versions/1/comparison`: one row for field `customer_id`'s id with `["renamed"]`, `order_id` with `["type_changed", "nullability_changed"]`, `["shipping", "zip"]` `["added"]` at depth 1; `?base=9` → 404.
  - `partition-spec-versions`: `default_spec_id` 1; `partition-spec-versions/1/comparison`: one `transform_changed` row, `previous_expression` `day(order_ts)`, `expression` `hour(order_ts)`.
  - `GET /api/v1/tables/{uuid}/commits` (uuid from the console or `GET /api/v1/tables`, once maintenance manages the table, see Step 5): three commits with `schema_id` 0, 1, 1.
- [ ] **Step 5: Console checks** at `http://localhost:8591/console/` (logged in as `platform-admin`): the table's Schema tab shows `v1` `Current` with "+1 added · 1 renamed · 1 type changed · 1 nullability changed", the comparison lists `shipping.zip` indented, "Show changes only" hides `order_ts`, "Compare with" `v0` on `v1` and back; the partition panel reads `day(order_ts) → hour(order_ts)` with `Default` on `v1`; the DDL note names `v1`. Once maintenance manages the table (the discovery rule for `iceberg / inventory / *` that KCL-96's batch step adds covers `schema_demo`; after KCL-71, a discovery policy on `iceberg.inventory`; the Overview says "Maintenance: managed" and its Reconciliations tab shows a first check with `table_managed`), the Commits tab shows `v0` / `v1` links and `v0` lands on the Schema tab with `v0` selected. At phone width (browser devtools, 390px) neither tab scrolls sideways. Delete `schema_demo` from the console afterwards.
- [ ] **Step 6:** `GATE` (all scopes); add the `docs/agents/project-history.md` line (after KCL-96's) (2026-11-2x: KCL-97: the catalog table keeps every schema, spec and snapshot schema id; the four version routes; comparisons by field id with transform changes paired by source column; `DiffList` in the design system; the Schema tab's version lists and the Commits tab's schema link; verified on a rebuilt cluster), commit it `docs: record schema and partition spec version comparison (KCL-97)`, record the results on KCL-97 in a dated comment, and push only when the user asks.
