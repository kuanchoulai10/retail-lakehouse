# Catalog Context and Catalog Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `catalog` bounded context that serves every catalog operation of the upstream Polaris console through our API, and console pages (Catalogs → catalog → namespace → table/view/generic table) built on it, with one table page that joins Polaris facts and maintenance facts.

**Architecture:** `src/data-platform/backend/context/catalog/` holds five aggregates (`catalog`, `namespace`, `table`, `generic_table`, `view`), each loaded and saved through a `{Aggregate}Repo` port whose adapter talks to Polaris over HTTP (httpx). One Gateway grants content rights to a new catalog's `catalog_admin` role. Bootstrap mounts both contexts' routers on one FastAPI app. The console composes the table page from the catalog API and the maintenance API; the contexts never import each other.

**Tech Stack:** Python 3.14, FastAPI, httpx, pytest, import-linter, ruff, ty; React, TanStack Query and Table, shadcn/ui, vitest; Helm and bash for wave 25.

**Spec:** `docs/superpowers/specs/2026-11-07-catalog-context-design.md`. Read it before any task; its "(owner)" lines are binding.

## Global Constraints

- Backend rules in `src/data-platform/backend/CLAUDE.md` apply to every file: one object per file, boundary-only imports, `__all__` re-exports, ABC ports, StrEnum, `from __future__ import annotations`, port / DTO naming tables, no infrastructure words under `application/` (`polaris`, `iceberg_rest`, `sql`, ... are banned; `iceberg`, `catalog`, `http` are allowed).
- Frontend rules in `src/data-platform/frontend/CLAUDE.md` apply, including token-only colours (`test/noRawColors.test.ts`).
- Root `CLAUDE.md`: no `cd`, `uv run`, TDD, conventional commits (lowercase subject, lines ≤ 100 chars, message ends with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`), `KUBE_CONTEXT=retail-lakehouse` for wave scripts.
- Every commit passes `task pre-pr` (from the repo root). Frontend commits also pass `npm --prefix src/data-platform/frontend run typecheck`, `run lint`, `test -- --run`, `run build`.
- Polaris 1.8.0; base URL `http://polaris.lakehouse-catalog.svc.cluster.local:8181`; Iceberg REST under `/api/catalog/v1/{prefix}` with prefix = catalog name; generic tables under `/api/catalog/polaris/v1/{prefix}/namespaces/{ns}/generic-tables`; management under `/api/management/v1`; token `POST /api/catalog/v1/oauth/tokens` (client credentials, scope `PRINCIPAL_ROLE:ALL`). Namespace parts are joined with `\x1f` in Polaris URLs.
- The backend keeps the existing credential (`GLAC_CATALOG__CREDENTIAL`, root principal). No caching of catalog data anywhere.
- Dropping a table never purges (`purgeRequested=false`). No cascade deletes.
- The old console route `/tables/:uuid` is removed with no redirect.
- Maintenance covers only `CatalogSettings.names`. Do not change discovery or Spark config.
- Do not touch on-hold paths listed in the root `CLAUDE.md`.

## Review Focus

1. Namespace parts that contain `.` or spaces (`a.b` as one part): API and console URLs must round-trip them unchanged. Test in Task 4 (`test_namespace_part_with_dot_round_trips`) and Task 9 (`namespace path with a dot part links and loads`).
2. A Polaris 403 (for example, writing to a catalog without the content grant): user sees 403 with Polaris's message, never a 500 or a success. Test in Task 3 (`test_polaris_forbidden_maps_to_permission_denied`) and Task 3 route test (`test_permission_denied_maps_to_403`).
3. Polaris unreachable or token refresh failing mid-session: API answers 502 with a message, the next request retries the token. Test in Task 3 (`test_expired_token_is_refreshed_once`, `test_connect_error_maps_to_unavailable`).
4. Two people editing the same table's properties: the second save gets 409 "changed since you loaded it, reload". Test in Task 5 (`test_update_properties_conflict_on_replaced_table`) and Task 10 (`properties conflict shows reload message`).
5. A table renamed through our API while the maintenance list still shows the old name: the old link lands on the table page not-found state with a link to its namespace. Test in Task 10 (`missing table shows renamed-or-dropped state`).

---

## File Structure

Backend, all under `src/data-platform/backend/` (B):

```
context/catalog/
  __init__.py                                   # structural docstring only
  application/
    exceptions/{not_found_error,conflict_error,validation_error,
                permission_denied_error,catalog_unavailable_error}.py
    domain/model/{catalog,namespace,table,generic_table,view}/   # aggregate, id, value objects
    domain/service/shared/__init__.py           # ring exists (import-linter needs all four)
    port/inbound/{aggregate}/{verb_noun}/{use_case,input,output}.py
    port/outbound/{aggregate}/{aggregates}_repo.py
    port/outbound/catalog/create_catalog_content_grant/{gateway,input}.py
    service/{aggregate}/{verb_noun}.py
  adapter/
    inbound/web/{register_routes,error_handlers}.py
    inbound/web/shared/{web_use_cases,use_cases_dependency}.py
    inbound/web/{aggregate}/{router,dto}.py
    outbound/shared/polaris/{polaris_http_client,polaris_error_mapper}.py
    outbound/{aggregate}/polaris/{aggregates}_polaris_repo.py (+ mappers)
    outbound/catalog/polaris/create_catalog_content_grant_polaris_gateway.py
bootstrap/container/{create_api_app,build_catalog_web_use_cases,build_polaris_http_client}.py
bootstrap/configs/catalog_settings.py           # + management_uri
tests/context/catalog/...                       # mirrors the context, fakes under fakes/
```

Frontend, under `src/data-platform/frontend/src/` (F): `api/catalogTypes.ts`, `components/{Breadcrumbs,ConfirmDeleteDialog,MaintenanceEmptyState,ResourceListPage,ActionsMenu}.tsx`, `pages/{CatalogsPage,CatalogPage,NamespacePage,TablePage,ViewPage,GenericTablePage}.tsx`, `components/tabs/{SchemaTab,SnapshotsTab}.tsx`, `lib/catalogPaths.ts`.

## Shared decisions (every task uses these names)

- **Ids** (`domain/model/<agg>/<agg>_id.py`, each `@dataclass(frozen=True) class X(EntityId)`): `value` is the parts joined by `"\x1f"`. Each has `classmethod of(...)` and read-only properties:
  - `CatalogId.of(name: str)`; `.name`
  - `NamespaceId.of(catalog: str, parts: tuple[str, ...])`; `.catalog`, `.parts`
  - `TableId.of(catalog: str, namespace: tuple[str, ...], name: str)`; `.catalog`, `.namespace`, `.name` (same for `GenericTableId`, `ViewId`)
- **Repos** (`port/outbound/<agg>/<aggs>_repo.py`, extend `Repository[Agg]`, re-export the aggregate and id from the package): `get`, `create`, `delete(id)` everywhere; `list_all` implemented by walking every catalog (unused by services); plus
  - `CatalogsRepo.update(catalog) -> Catalog`
  - `NamespacesRepo.list_in(catalog: CatalogId, parent: tuple[str, ...]) -> list[Namespace]`, `.update_properties(id, updates: dict[str,str], removals: list[str]) -> Namespace`
  - `TablesRepo.list_in(namespace: NamespaceId) -> list[TableId]`, `.rename(source: TableId, target: TableId) -> None`, `.update_properties(id, expected_uuid: str, updates, removals) -> Table`
  - `GenericTablesRepo.list_in(namespace) -> list[GenericTableId]`, `ViewsRepo.list_in(namespace) -> list[ViewId]`
- **Exceptions** (`application/exceptions`): `NotFoundError`, `ConflictError`, `ValidationError`, `PermissionDeniedError`, `CatalogUnavailableError`; each carries the upstream message as `str(exc)`. Web status: 404, 409, 422, 403, 502; body `{"detail": str(exc)}`.
- **Polaris status mapping** (`polaris_error_mapper.py`, `raise_for_polaris(response: httpx.Response) -> None`): 400/422 → ValidationError, 401/403 → PermissionDeniedError, 404 → NotFoundError, 409 → ConflictError, other ≥ 400 and `httpx.TransportError` → CatalogUnavailableError. Message = Polaris `error.message` when the body has it, else the raw text.
- **API routes** (prefix `/v1`; `{ns}` is parts joined by `\x1f`, URL-encoded as `%1F`):
  - `GET|POST /catalogs`, `GET|PUT|DELETE /catalogs/{catalog}`
  - `GET|POST /catalogs/{catalog}/namespaces?parent={ns}`, `GET|DELETE /catalogs/{catalog}/namespaces/{ns}`, `PUT /catalogs/{catalog}/namespaces/{ns}/properties`
  - `GET|POST /catalogs/{catalog}/namespaces/{ns}/tables`, `GET|DELETE .../tables/{table}`, `PUT .../tables/{table}/properties`, `POST .../tables/{table}/rename`
  - `GET|POST .../generic-tables`, `GET|DELETE .../generic-tables/{name}`; `GET|POST .../views`, `GET|DELETE .../views/{name}`
  - Create returns 201, delete 204.
- **Use case names** (inbound port dirs, `snake_case` of these): ListCatalogs, GetCatalog, CreateCatalog, UpdateCatalog, DeleteCatalog; ListNamespaces, GetNamespace, CreateNamespace, DeleteNamespace, UpdateNamespaceProperties; ListTables, GetTable, CreateTable, DeleteTable, RenameTable, UpdateTableProperties; ListGenericTables, GetGenericTable, CreateGenericTable, DeleteGenericTable; ListViews, GetView, CreateView, DeleteView.
- **Fields and forms:** each create/update request carries the fields of the matching upstream form in `~/Projects/polaris-tools/console/src/components/forms/` (`CreateCatalogModal`, `EditCatalogModal`, `CreateNamespaceModal`, `CreateTableModal`, `EditTablePropertiesModal`, `RenameTableModal`, `CreateViewModal`) and the request types in its `src/types/api.ts`. Copy the field set, not the code.

---

### Task 1: Let architecture tests accept a context without Temporal or an event consumer

**Files:**
- Modify: `B/tests/architecture/test_directory_structure.py`, `test_adapter_layout.py`, `test_aggregate_axis.py`, `test_temporal_workflow_determinism.py`, `test_import_boundary.py:320`
- Modify: `B/tests/architecture/fixture_context.py` (if needed for new tests)
- Modify: `B/CLAUDE.md` ("Known limitation" paragraph, "Gateway directory structure" paragraph), `docs/agents/known-follow-ups.md` (drop the `>= 5` entry)

**Interfaces:** Produces the rule set Tasks 3–6 build against:
- a context must have `adapter/inbound/web` and `adapter/outbound`;
- `adapter/inbound/event_consumer` and `adapter/hybrid/<tech>` are optional;
- a hybrid tech dir, if present, holds exactly `{inbound, outbound, contracts}`;
- every aggregate has exactly one `*_repo.py` port in its own context.

- [ ] **Step 1: Write the failing tests** with the `fixture_context.py` helpers. Each builds a tmp context holding only `application/` (all four rings), `adapter/inbound/web/` and `adapter/outbound/`, and asserts:
  - `test_context_without_hybrid_or_event_consumer_passes_layout`: the layout rules pass;
  - `test_hybrid_without_temporal_is_allowed`;
  - `test_partial_temporal_dir_still_fails`: a `hybrid/temporal` with only `inbound` fails;
  - `test_workflow_modules_found_when_temporal_present`: the determinism check is skipped for contexts without `adapter/hybrid/temporal`;
  - `test_each_aggregate_has_one_repository_port_per_context`: it replaces the global `>= 5`, compares the repo ports under `{ctx}.application.port.outbound.{agg}` with `aggregates(ctx)` for every context, and fails when one is missing.
- [ ] **Step 2:** Run `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/architecture -q`. Expected: the new tests FAIL.
- [ ] **Step 3:** Change the checks to "only if present", as listed under Interfaces. Do not name any context; `test_architecture_tests_name_no_context` must stay green. Update the two CLAUDE.md paragraphs:
  - remove the "Known limitation" text;
  - say that extra gateway files are the fixed allowlist `GATEWAY_EXTRA_FILES` in `test_outbound_port_structure.py`.
- [ ] **Step 4:** Run the architecture tests again. Expected: everything passes, table_maintenance included.
- [ ] **Step 5:** Commit: `test(backend): let a context omit temporal and the event consumer`.

### Task 2: Compose the API app in bootstrap

**Files:**
- Rename: `B/context/table_maintenance/adapter/inbound/web/create_app.py` → `register_routes.py`, exporting `register_routes(app: FastAPI, use_cases: WebUseCases) -> None`. It stores the use cases at `app.state.table_maintenance_use_cases`, registers the error handlers, and mounts the five routers under `/v1`.
- Modify: TM `web/shared/use_cases_dependency.py`, which reads `app.state.table_maintenance_use_cases`. Also TM `web/__init__.py`, and `test_aggregate_axis.py`, whose web-root allowlist becomes `{"__init__.py", "register_routes.py", "error_handlers.py"}`.
- Create: `B/bootstrap/container/create_api_app.py` with `create_api_app(*registrations: Callable[[FastAPI], None]) -> FastAPI`. It builds `FastAPI(title="Data Platform API")`, adds `GET /healthz` → `{"status": "ok"}`, then applies each registration.
- Modify: `B/bootstrap/container/build_api_app.py`, which calls `create_api_app(lambda app: register_routes(app, build_web_use_cases(use_cases)))`.
- Modify tests: `tests/context/table_maintenance/adapter/inbound/web/web_test_support.py` (`build_client` uses `FastAPI()` + `register_routes`), `tests/bootstrap/container/test_build_api_app.py`, `test_build_web_use_cases.py`.

**Interfaces:** Produces `create_api_app` and the `register_routes(app, use_cases)` convention. Task 3 adds the catalog registration.

- [ ] **Step 1:** Write the failing tests:
  - `test_create_api_app_serves_healthz_and_applies_registrations` in `tests/bootstrap/container/test_create_api_app.py`: two fake registrations each add a route; both routes answer, and `/healthz` returns 200 with `{"status": "ok"}`.
  - `test_register_routes_mounts_table_routes_under_v1`: `GET /v1/tables` reaches the stub.
- [ ] **Step 2:** Run them. Expected: FAIL, because the module does not exist.
- [ ] **Step 3:** Implement as listed under Files.
- [ ] **Step 4:** Run the full backend suite and `lint-imports`. Expected: everything passes, with the existing route tests unchanged in behaviour.
- [ ] **Step 5:** Commit: `refactor(backend): compose the api app in bootstrap`.

### Task 3: Catalog context foundation and the `catalog` aggregate

**Files:**
- Create the `context/catalog` skeleton from the File Structure: the four application rings (`domain/service/shared/__init__.py` holds a docstring only), exceptions, web `register_routes.py` and `error_handlers.py`, web shared, the `adapter/outbound/shared/polaris/` client and mapper. Mirror it all under `tests/context/catalog/`, with `test_boundary_samples.py` modelled on table_maintenance's.
- Create the `catalog` aggregate:
  - `domain/model/catalog/{catalog,catalog_id,catalog_type,storage_config}.py`. `Catalog(AggregateRoot[CatalogId])` has name, type (`CatalogType` StrEnum: INTERNAL, EXTERNAL), properties `dict[str,str]`, storage_config, entity_version `int`, created_at / updated_at `datetime | None`.
  - The five use cases.
  - `CatalogsRepo`.
  - The gateway `CreateCatalogContentGrantGateway`, with input `CreateCatalogContentGrantGatewayInput(catalog_name: str)` and method `create(input) -> None`.
  - `CatalogsPolarisRepo` and `CreateCatalogContentGrantPolarisGateway`.
  - The router and DTOs.
- Modify:
  - `B/bootstrap/configs/catalog_settings.py`: add `management_uri: str = "http://polaris.lakehouse-catalog.svc.cluster.local:8181/api/management/v1"`.
  - `B/pyproject.toml`: add `httpx` as a runtime dep, then run `uv lock` and the requirements export hook.
  - `B/.importlinter`: add `httpx` to the forbidden lists of `domain-pure` and `application-no-outer-rings`.
  - Bootstrap: `build_polaris_http_client.py` and `build_catalog_web_use_cases.py`, and `build_api_app.py` adds the catalog registration.
  - `B/tests/architecture/test_aggregates.py`: pin catalog's aggregate set the same way table_maintenance's is pinned. This is the only architecture test allowed to name contexts.

**Interfaces:**
- `PolarisHttpClient(base_uri: str, management_uri: str, credential: str, scope: str, client: httpx.Client)` provides `catalog_request(method, path, *, json=None, params=None) -> httpx.Response` and `management_request(...)`. It fetches the token lazily. On a 401 it refreshes the token once and retries, and every response passes through `raise_for_polaris`.
- `CreateCatalogService.execute` creates the catalog, then calls the grant gateway. If the grant fails, it re-raises with the message `catalog <name> was created but the content grant failed: <polaris message>`. The catalog is left in place; that is the builder's call per the spec, and this plan decides it.
- `UpdateCatalogService` sends the `entity_version` read by the caller. Polaris's 409 becomes `ConflictError("catalog <name> changed since you loaded it, reload")`.

- [ ] **Step 1:** Write the failing client and mapper tests. Use `httpx.MockTransport`; no network.
  - `test_token_fetched_with_client_credentials_and_scope`
  - `test_expired_token_is_refreshed_once`
  - `test_polaris_forbidden_maps_to_permission_denied`: the message is taken from `{"error":{"message":...}}`
  - `test_conflict_maps_to_conflict`, `test_not_found_maps_to_not_found`, `test_connect_error_maps_to_unavailable`
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement the client and the mapper.
- [ ] **Step 4:** Write the failing service tests, using fakes `InMemoryCatalogsRepo` and `RecordingCreateCatalogContentGrantGateway` under `tests/context/catalog/fakes/`:
  - `test_create_catalog_grants_content_to_catalog_admin`
  - `test_create_catalog_reports_grant_failure_without_claiming_success`
  - `test_update_catalog_conflict_says_reload`
  - `test_delete_unknown_catalog_is_not_found`
  - `test_list_catalogs_returns_every_catalog`
- [ ] **Step 5:** Write the failing Polaris adapter tests with MockTransport. They assert the exact requests:
  - `POST /api/management/v1/catalogs` with body `{"catalog": {...}}`;
  - `PUT .../catalogs/{name}` with `currentEntityVersion`;
  - `DELETE .../catalogs/{name}`;
  - `PUT .../catalogs/{name}/catalog-roles/catalog_admin/grants` with `{"grant":{"type":"catalog","privilege":"CATALOG_MANAGE_CONTENT"}}`.
- [ ] **Step 6:** Write the failing route tests:
  - `test_create_catalog_returns_201`
  - `test_permission_denied_maps_to_403`
  - `test_unavailable_maps_to_502`
  - `test_delete_catalog_returns_204`
- [ ] **Step 7:** Implement the domain, ports, services, adapters, router, DTOs and bootstrap wiring until Steps 4–6 pass.
- [ ] **Step 8:** Run `task pre-pr`. Expected: green, with all architecture tests passing for both contexts.
- [ ] **Step 9:** Commit in two commits:
  - `feat(catalog): add the catalog context foundation and polaris client`
  - `feat(catalog): manage catalogs through the api`

### Task 4: `namespace` aggregate

**Files:** the `namespace` aggregate: domain `Namespace(AggregateRoot[NamespaceId])` with properties, the five use cases, `NamespacesRepo`, `NamespacesPolarisRepo`, router and DTOs, wiring; tests mirrored.

**Interfaces:**
- Consumes the Task 3 client, exceptions and `CatalogId`.
- `ListNamespacesUseCaseInput(catalog: str, parent: list[str])` returns direct children only, as Iceberg REST `GET /namespaces?parent=` does.
- `UpdateNamespacePropertiesUseCaseInput(catalog, namespace: list[str], updates: dict[str,str], removals: list[str])` calls `POST /api/catalog/v1/{catalog}/namespaces/{ns}/properties`.

- [ ] **Step 1:** Write the failing tests:
  - `test_namespace_part_with_dot_round_trips`, at service, adapter and route level: the part `a.b` is sent to Polaris as one part (`a.b` stays one `\x1f`-separated element) and comes back unchanged;
  - `test_list_namespaces_returns_direct_children`;
  - `test_create_namespace_with_properties`;
  - `test_delete_non_empty_namespace_reports_polaris_error`: Polaris 409 or 400 passes through with its message;
  - `test_update_namespace_properties_sends_updates_and_removals`;
  - route `test_namespace_path_uses_unit_separator`.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `task pre-pr`. Expected: green.
- [ ] **Step 5:** Commit: `feat(catalog): manage namespaces through the api`.

### Task 5: `table` aggregate (Iceberg tables)

**Files:** the `table` aggregate:
- `domain/model/table/`: `Table`, `TableId`, `TableSchema`, `SchemaField`, `PartitionSpec`, `SortOrder`, `Snapshot`, `TableSummary`;
- the six use cases;
- `TablesRepo`;
- `TablesPolarisRepo` plus one mapper per value object, from the `LoadTableResult.metadata` JSON;
- router, DTOs and wiring; tests mirrored.

**Interfaces:**
- `GetTableUseCaseOutput` carries everything the console's Schema, Snapshots, Properties and Overview-top panels need:
  - `uuid`, `format_version`, `location`, `current_snapshot_id`, `last_updated_ms`;
  - `schema` (fields: id, name, type as a string, required, doc), `partition_spec`, `sort_order`;
  - `snapshots` (id, parent_id, timestamp_ms, operation, summary dict);
  - `properties`;
  - `summary`, with record and file counts and total size, taken from the current snapshot's summary keys `total-records`, `total-data-files` and `total-files-size` when present, else null.

  Every field is primitive.
- `DeleteTableService` calls `DELETE .../tables/{t}?purgeRequested=false`.
- `RenameTableUseCaseInput(catalog, namespace, name, target_namespace: list[str], target_name: str)` calls `POST /api/catalog/v1/{catalog}/tables/rename`.
- `UpdateTablePropertiesUseCaseInput(catalog, namespace, name, expected_uuid: str, updates, removals)` sends `requirements: [{"type":"assert-table-uuid","uuid": expected_uuid}]` and `updates: [{"action":"set-properties",...},{"action":"remove-properties",...}]`. A failed requirement (Polaris 409) becomes `ConflictError("table <name> changed since you loaded it, reload")`.
- `CreateTableUseCaseInput` takes the CreateTableModal field set (name, schema fields, optional partition fields, optional location, properties).

- [ ] **Step 1:** Write the failing tests:
  - `test_load_maps_schema_partition_sort_snapshots_and_summary`, using a fixture `LoadTableResult` JSON from a real Iceberg v2 table and saved under `tests/context/catalog/adapter/outbound/table/polaris/fixtures/`;
  - `test_drop_table_never_purges`;
  - `test_rename_sends_source_and_destination`;
  - `test_update_properties_conflict_on_replaced_table`;
  - `test_update_properties_sends_assert_table_uuid`;
  - `test_create_table_sends_schema_and_partition_spec`;
  - route `test_get_unknown_table_returns_404`.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `task pre-pr`. Expected: green.
- [ ] **Step 5:** Commit: `feat(catalog): manage iceberg tables through the api`.

### Task 6: `generic_table` and `view` aggregates

**Files:** two aggregates with the same shape as Task 5 but fewer operations: list, get, create and delete each. Tests are mirrored.

**Interfaces:**
- `GetGenericTableUseCaseOutput`: name, format, base_location, doc, properties.
- `GetViewUseCaseOutput`: name, uuid, sql, dialect, default_namespace, schema fields, versions (version_id, timestamp_ms, sql), properties.
- `CreateViewUseCaseInput` takes the CreateViewModal field set. `CreateGenericTableUseCaseInput` takes name, format, base_location, doc and properties.

- [ ] **Step 1:** Write the failing tests:
  - `test_generic_table_paths_use_polaris_api_prefix`: the request goes to `/api/catalog/polaris/v1/...`;
  - `test_load_view_maps_current_version_sql`;
  - `test_create_view_sends_view_version`;
  - `test_delete_view_and_generic_table_return_204`, at route level.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `task pre-pr`. Expected: green.
- [ ] **Step 5:** Commit: `feat(catalog): manage views and generic tables through the api`.

### Task 7: Maintenance lists the catalogs it covers

**Files:** in table_maintenance, under `table_discovery_settings`:
- inbound port `list_covered_catalogs` (`ListCoveredCatalogsUseCase`, output `ListCoveredCatalogsUseCaseOutput(catalogs: list[str])`);
- `ListCoveredCatalogsService(catalog_names: Sequence[str])`;
- route `GET /v1/table-discovery-settings/catalogs` returning `{"catalogs": [...]}`;
- wiring from `settings.catalog.names`.

- [ ] **Step 1:** Write the failing tests: service `test_list_covered_catalogs_returns_configured_names`, and route `test_covered_catalogs_route`.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run `task pre-pr`. Expected: green.
- [ ] **Step 5:** Commit: `feat(table-maintenance): list the catalogs maintenance covers`.

### Task 8: Console building blocks

**Files (F):**
- `api/client.ts`: `apiSend` also accepts `"DELETE"`.
- `api/catalogTypes.ts`: types mirroring the Task 3–6 DTOs.
- `lib/catalogPaths.ts`: `catalogPath(c)`, `namespacePath(c, ns: string[])`, `tablePath(c, ns, t, tab?)`, `viewPath`, `genericTablePath`, and `apiNamespace(ns: string[])`, which joins with `\x1f` and encodes. They are the only place URLs are built.
- `components/Breadcrumbs.tsx`: linked crumbs. `PageHeader` takes `breadcrumbs: Crumb[]` instead of the string; existing callers are updated.
- `components/ConfirmDeleteDialog.tsx`: props `objectKind`, `objectName`, `fullPath`, `onConfirm`, `isPending`, `error`. The Delete button is enabled only when the typed text equals `objectName`.
- `components/MaintenanceEmptyState.tsx`: prop `reason: "catalog-not-covered" | "not-found" | "excluded" | "dropped"`, with the exact messages from the spec. `not-found` links to `/discovery-rules`.
- `components/ResourceListPage.tsx`: title, breadcrumbs, columns, rows, a `New` button that opens a caller-supplied form dialog, and per-row delete through `ConfirmDeleteDialog`.
- `components/ActionsMenu.tsx`: a dropdown of `{label, onSelect}` items.
- `components/AppShell.tsx`: add a `Catalog` nav item at `/catalogs`, active for `/catalogs/*`. The spec says "top navigation", but the console's nav is the `NAV_ITEMS` sidebar, so the new item goes there.

- [ ] **Step 1:** Write the failing tests:
  - `catalogPaths.test.ts`: `namespace path with a dot part links and loads`, which asserts `apiNamespace(["a.b","c"]) === "a.b%1Fc"`, and that the console routes round-trip;
  - `ConfirmDeleteDialog.test.tsx`: `delete stays disabled until the exact name is typed`, and `shows the polaris error and stays open`;
  - `MaintenanceEmptyState.test.tsx`: one test per reason, checking the message text and that only `not-found` links;
  - `Breadcrumbs.test.tsx`: `every crumb but the last is a link`.
- [ ] **Step 2:** Run `npm --prefix src/data-platform/frontend test -- --run`. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the four frontend checks. Expected: green.
- [ ] **Step 5:** Commit: `feat(console): add the catalog page building blocks`.

### Task 9: Catalogs, catalog and namespace pages

**Files (F):**
- `pages/CatalogsPage.tsx` at `/catalogs`;
- `pages/CatalogPage.tsx` at `/catalogs/:catalog`: a list of top-level namespaces, plus catalog properties and storage, with Actions → Edit, Delete;
- `pages/NamespacePage.tsx` at `/catalogs/:catalog/namespaces/:ns`: child namespaces, then one list of tables, views and generic tables with a Type column, plus properties, with Actions → Edit properties, Delete;
- create and edit form dialogs under `components/forms/`, with the field sets named in "Shared decisions";
- routes in `App.tsx`.

Every write refetches with `queryClient.invalidateQueries` on the affected keys. Nothing is patched locally.

- [ ] **Step 1:** Write the failing tests with stubbed fetch, in the style of `TablePage.test.tsx`:
  - `catalogs page lists catalogs and creates one`, which asserts the POST body and the refetch after it;
  - `catalog page lists namespaces with breadcrumbs`;
  - `namespace page lists tables views and generic tables with a type column`;
  - `deleting a non-empty namespace shows the polaris message`;
  - `catalog edit conflict shows reload message`.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the four frontend checks. Expected: green.
- [ ] **Step 5:** Commit: `feat(console): browse and edit catalogs and namespaces`.

### Task 10: One table page, plus view and generic table pages

**Files (F):**
- `pages/TablePage.tsx` is rewritten for `/catalogs/:catalog/namespaces/:ns/tables/:table/:tab?` with the tabs Overview, Schema, Snapshots, Commits, Maintenance, Properties, Settings. It loads the catalog table, then the maintenance table with the existing `GET /v1/tables/{uuid}`, passing the catalog table's `uuid`. The two queries are independent; the maintenance tabs wait for both.
- The table header takes rows, files, size and snapshots from the catalog summary. Pause/Resume and Run maintenance show only when the table is managed.
- `components/tabs/SchemaTab.tsx` (fields, partition spec, sort order, DDL generated client-side) and `SnapshotsTab.tsx`.
- `OverviewTab`: the top part from the catalog, plus the managed marker; the bottom part has the existing panels or `MaintenanceEmptyState`.
- `CommitsTab`, `MaintenanceTab` and `SettingsTab` render `MaintenanceEmptyState` when unmanaged.
- `PropertiesTab` reads the catalog table.
- Actions: Rename (a dialog with target namespace and name; after success, navigate to the new URL), Edit properties (sends `expected_uuid`), Delete (`ConfirmDeleteDialog`, then go to the namespace page).
- `pages/ViewPage.tsx` and `pages/GenericTablePage.tsx` are the fixed pages from the spec, with Actions → Delete only.
- `TableListPage.tsx`: rows link with `tablePath(...)`; `dropped` rows have no link.
- Remove the `/tables/:uuid/:tab?` route, and remove `invalidateTableState`'s `metadata` key.

**Interfaces:** the managed reason is worked out in this order:
1. the catalog name is not in `GET /v1/table-discovery-settings/catalogs` → `catalog-not-covered`;
2. maintenance answers 404 → `not-found`;
3. status `excluded` → `excluded`; status `dropped` → `dropped`;
4. otherwise managed.

- [ ] **Step 1:** Write the failing tests:
  - `every table shows the same seven tabs`, for a managed and an unmanaged table;
  - `unmanaged table shows the empty state on commits maintenance and settings`, one per reason;
  - `managed marker on overview`;
  - `rename navigates to the new url`;
  - `properties conflict shows reload message`;
  - `missing table shows renamed-or-dropped state`, which links to the namespace page;
  - `maintenance list links to the catalog path and dropped rows have no link`;
  - `view page shows sql and only delete`;
  - `old tables uuid route renders not found`.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the four frontend checks. Expected: green.
- [ ] **Step 5:** Commit: `feat(console): one table page joining catalog and maintenance`.

### Task 11: Remove maintenance's table metadata route

**Files:** in table_maintenance, remove:
- `port/inbound/table/get_table_metadata/` and `service/table/get_table_metadata.py`;
- the `/metadata` route and its DTO;
- `WebUseCases.get_table_metadata` and the bootstrap fields;
- `describe_table`, `TableDescription` and `description_mapper.py`, if nothing else uses them. Check this with `git grep`.

Also remove their tests and fakes, and the e2e use at `platform/25-lakehouse-control-plane/e2e.sh:409-422` (Task 12 replaces it).

- [ ] **Step 1:** Run `git grep -n -E 'get_table_metadata|describe_table|TableDescription|/metadata'` across the backend, the frontend and platform/25, and list every hit in the report.
- [ ] **Step 2:** Delete the code and update the callers. Then add the regression test `test_table_metadata_route_is_gone`: `GET /v1/tables/{uuid}/metadata` must return 404 or 405.
- [ ] **Step 3:** Run `task pre-pr` and the frontend checks. Expected: green.
- [ ] **Step 4:** Commit: `refactor(table-maintenance): drop the table metadata route the catalog now serves`.

### Task 12: Deploy, prove the round trips, record the work

**Files:**
- `platform/25-lakehouse-control-plane/chart/templates/configmap.yaml`: add `GLAC_CATALOG__MANAGEMENT_URI`.
- `e2e.sh`: add a catalog round trip for each object type: catalog, namespace, table, generic table, view.
  - Write through our API, using the existing `api()` helper.
  - Read back through Polaris directly, from the api pod, with a token obtained from `GLAC_CATALOG__CREDENTIAL` inside the pod. Never print the credential or the token.
  - Compare the written and read-back values.
  - Cover a properties update with `expected_uuid`, a rename, and every delete. After each delete, Polaris must return 404.
  - Create the round-trip catalog `tm_e2e_catalog_<timestamp>` and its storage base under the existing bucket, then delete everything at the end, including on failure.
- Replace the `/metadata` use from Task 11 with `GET /v1/catalogs/iceberg/namespaces/<ns>/tables/<t>`.
- `validate.sh`: replace `/console/tables/x/commits` with `/console/catalogs`, and add `api_get /v1/catalogs`.
- Docs:
  - `docs/agents/project-history.md`: one line;
  - `src/data-platform/backend/CLAUDE.md`: the context list now holds two contexts, catalog's aggregates, and the `register_routes` convention;
  - `src/data-platform/frontend/CLAUDE.md`: the page pattern, `ResourceListPage`, `ConfirmDeleteDialog` and `MaintenanceEmptyState`;
  - `docs/agents/known-follow-ups.md`: "maintenance follows every catalog" and "catalog pages show no catalog roles until access";
  - root `CLAUDE.md`: the current bounded context sentence.

- [ ] **Step 1:** `bash -n` both scripts, then run `task pre-pr`.
- [ ] **Step 2:** Run `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh`, then `validate.sh`, then `e2e.sh`. All three must exit 0. The reclaimed flake (`N < 20`) gets one rerun.
- [ ] **Step 3:** Run `kubectl get pods --namespace lakehouse-control-plane --context retail-lakehouse`. Expect new backend and console tags and 0 restarts.
- [ ] **Step 4:** Commit: `test(platform): prove the catalog api round trips through polaris`, plus `docs: record the catalog context`.
- [ ] **Step 5:** Stop. Do not push. The controller tells the owner.
