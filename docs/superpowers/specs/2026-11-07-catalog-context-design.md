# Catalog context and catalog pages: design

Date: 2026-11-07. Status: draft, waiting for owner approval. The builder-check questions are answered: owner answers are marked "(owner)", and my own decisions are marked "(my call)".

## Intent

The owner wants the data platform console to do everything the upstream Polaris console does, through our own API. Today the upstream console runs as a spike next to ours (`~/Projects/polaris-tools/console`), and it calls Polaris directly. This project covers the catalog half of that console: catalogs, namespaces, tables and views, read and write. The other half (principals, roles, grants) is the later `access` context.

A table is one thing to the user. Its Polaris facts (schema, snapshots, properties) and our maintenance facts (commits, maintenance runs, settings) belong on one page.

The owner's top priority is **consistency**: one page design that works for every table, and the same pattern on every list page. A page that looks different depending on the table is a failure, even if it works.

## Goals

1. A new bounded context `catalog` in `src/data-platform/backend/context/catalog/`. Polaris is the source of truth (ADR 0005). It covers every catalog operation the Polaris console has:

   | Object | Operations | Polaris API used by the upstream console |
   |---|---|---|
   | Catalog | list, get, create, update, delete | management API `/catalogs` |
   | Namespace | list (nested), get, create, delete | Iceberg REST `/{prefix}/namespaces` |
   | Iceberg table | list, load (schema, partition spec, sort order, snapshots, properties, DDL), create, delete, rename, update properties | Iceberg REST `/{prefix}/namespaces/{ns}/tables`, `/{prefix}/tables/rename` |
   | Generic table | list, get, create, delete | Polaris API `/{prefix}/namespaces/{ns}/generic-tables` |
   | View | list, load, create, delete | Iceberg REST `/{prefix}/namespaces/{ns}/views` |

   The reference for each operation's fields and behaviour is the upstream console source: `console/src/api/catalog/*.ts`, `console/src/api/management/catalogs.ts` and the forms in `console/src/components/forms/`.
2. Our API exposes these operations, and the console calls only our API, never Polaris.
3. New console pages, using the drill-down layout the owner chose:
   - The top navigation gets a **Catalog** entry.
   - Pages: Catalogs → catalog page (its namespaces) → namespace page (its tables and views) → table page or view page.
   - A breadcrumb such as `Catalogs › iceberg › retail › orders` sits above every page below Catalogs.
   - Every list page has the same shape: a table of rows, plus a **New** button. Create and delete happen on the list page of the parent object.
4. One table page for every Iceberg table.
   - The tabs are Overview, Schema, Snapshots, Commits, Maintenance, Properties and Settings, on every table.
   - An **Actions** menu at the top right holds Rename, Edit properties and Delete.
   - The Polaris tabs (Overview, Schema, Snapshots, Properties) always have data.
   - The maintenance tabs (Commits, Maintenance, Settings) show one shared empty state when maintenance does not manage the table. The empty state says that no discovery rule includes the table, and it links to Discovery rules. It is one component, used by all three tabs.
   - Overview shows a small "Maintenance: managed / not managed" marker.
5. The table page URL is `/catalogs/<catalog>/namespaces/<namespace>/tables/<table>/<tab>`. **The old `/tables/<uuid>` route is removed, with no redirect** (owner decision). Every link that pointed at it, such as the maintenance table list, links to the new URL.

## Non-goals

- Principals, principal roles, catalog roles, grants and privileges. These belong to the `access` context, built later on Polaris built-in RBAC. Catalog pages do not show catalog roles in this project. The one exception is the fixed content grant made when a catalog is created; see "New catalogs can hold content".
- Maintenance for catalogs other than the ones in `CatalogSettings.names`.
- Keycloak + OPA "external principals". This is deferred; see `docs/agents/known-follow-ups.md`, SSO phase 3.
- Copying catalog data into our database, or caching it. Every read goes to Polaris.
- Polaris policies, connections to external or federated catalogs beyond what the catalog create and update forms already offer, and table data preview (Polaris has no query engine).
- The upstream console's global search, recently-viewed list and home page.

## Anti-goals

- Different page layouts or tab sets for different kinds of tables, such as managed vs unmanaged, or Iceberg tables in different catalogs.
- List pages that each invent their own create and delete flow.
- The console calling Polaris directly for anything in scope.
- The `catalog` context importing `table_maintenance`, or the reverse, outside the cross-context rule (ADR 0005, backend `CLAUDE.md`).
- **Deleting something by accident, above all a catalog** (owner). A single misclick must never delete anything.
- **Our API disagreeing with Polaris** (owner). This covers a page showing something Polaris does not hold, and a write that reports success when Polaris did not apply it. Once the console has refreshed, what it shows must be what Polaris holds.

## Decided how

- **Contexts.** `catalog` is its own context. It follows every existing backend rule: aggregate axis, four application rings, port and DTO naming, boundary-only imports, the import-linter contracts, and the ruff config. The rules are in `src/data-platform/backend/CLAUDE.md`.
- **Aggregates and ports.** Catalog objects are our aggregates even though Polaris holds the data (ADR 0006). So each is loaded and saved through a `{Aggregate}Repo` port, with a Polaris adapter named after the technology. An operation that is not loading or saving an aggregate uses a Gateway with one of the approved verbs. Rename is a probable example; the builder decides.
- **Linking to maintenance.** The catalog table and the maintenance `Table` are linked only by the Iceberg table UUID, as a value (ADR 0001 and 0005). The catalog API returns the table UUID.
- **Composition on the table page** (my call). The console composes the page from two API calls: the catalog API for the Polaris tabs, and the existing maintenance API for the maintenance tabs. A not-found from maintenance means "not managed". No backend use case joins the two contexts. This keeps the contexts independent and needs no cross-context port.
- **New catalogs can hold content** (owner). By default, Polaris creates a catalog's `catalog_admin` role without `CATALOG_MANAGE_CONTENT`. Today only `iceberg` gets that privilege, through the `polaris-create-catalog` job in `platform/21-polaris`.
  - Creating a catalog through our API therefore does two steps: it creates the catalog, then grants `CATALOG_MANAGE_CONTENT` on that catalog to that catalog's own `catalog_admin` role. The grant goes through a Gateway, since it is not saving the catalog aggregate. This way every catalog behaves the same.
  - If the grant fails, the create reports the failure with Polaris's error. It does not report success. The builder decides whether to delete the half-made catalog or to leave it and say so.
  - This fixed grant is the only access-related write in this project. General grant management stays in the `access` context.
- **Maintenance covers only the catalogs in `CatalogSettings.names`** (owner). Making maintenance follow every catalog is out of scope; add it to `docs/agents/known-follow-ups.md`.
  - A table in a catalog outside that list shows the shared empty state with the reason "this catalog is not covered by maintenance".
  - Detecting this reason needs a configured-catalogs list that the console can read. The builder decides the route, which can be a maintenance API that returns its covered catalog names.
- **What "managed" means** (my call).
  - A table counts as managed when maintenance has a `Table` for its UUID with status `active` or `paused`.
  - A not-found, `excluded` or `dropped` table counts as not managed.
  - The shared empty state is one component. It takes the reason and shows a matching message:
    - the catalog is not covered by maintenance: "this catalog is not covered by maintenance";
    - not found: "no discovery rule includes this table", linking to Discovery rules;
    - excluded: "excluded from maintenance by hand";
    - dropped: "maintenance recorded this table as dropped".
- **Overview content** (my call). Today's Overview shows only maintenance data: health, storage, freshness, recent commits and recent runs, from `/v1/tables/{uuid}/health`, `/storage`, `/commits` and `/table-maintenance-runs`. On the new page, Overview has two parts:
  - **Top part, from the catalog:** the table summary (format version, location, current snapshot, row and file counts where Polaris reports them, last updated) and the managed marker.
  - **Bottom part, from maintenance:** the existing maintenance panels when the table is managed, otherwise the shared empty state.

  The Properties tab and the table header read from the catalog API. Maintenance's `/v1/tables/{uuid}/metadata` route and its use case are removed if nothing else uses them; the builder checks.
- **Generic tables** (my call). A generic table is not an Iceberg table: it has no schema, no snapshots and no UUID, and Polaris cannot rename it or edit it. So it gets its own page, built like the view page:
  - the breadcrumb;
  - an Overview with format, location, doc and properties;
  - Actions holding only Delete.

  The anti-goal "same tab set" applies to every Iceberg table. Views and generic tables are other object types, and each type has one fixed page. On the namespace page they appear in the same list as tables, with a Type column.
- **Links from the maintenance list** (my call). Rows link with the catalog, namespace and name that maintenance stores. A row that is `dropped` has no link. After a rename, that stored name is stale until the Polaris event reaches the consumer. During that window a link can land on a missing table. The table page's not-found state then says the table may have been renamed or dropped, and links to its namespace page.
- **Existing maintenance table list** (my call). It stays, as the overview of the tables that maintenance manages. Its rows link to the new table URL. Browsing everything starts from Catalog.
- **View page** (my call). It shows the view's SQL, its schema, its versions and its properties, with the same breadcrumb and Actions pattern. Its Actions menu holds Delete only, because Polaris console has no view rename or edit.
- **Namespace properties** (my call). The namespace page shows its properties, and Edit properties is in its Actions menu. Iceberg REST supports updating them; the upstream console only shows them.
- **Deletes** (my call, from the owner's first anti-goal).
  - Every delete, of a catalog, namespace, table, generic table or view, uses the same dialog. The dialog names the object and its full path, and enables the Delete button only after the user types the object's name. One component serves every delete, for consistency.
  - Deleting a catalog or a namespace that is not empty fails with the error Polaris returns, shown to the user. There is no cascade.
  - Dropping a table does not purge its data files (`purgeRequested` stays false). Purge is not offered in this project.
- **Agreement with Polaris** (my call, from the owner's second anti-goal).
  - Nothing is cached in the backend. Every read goes to Polaris.
  - After every write the console refetches the affected objects from our API, and never shows locally patched state.
  - A Polaris error reaches the user with its status and message. It is never turned into a success or a generic failure.
  - Updates guard against lost writes where Polaris allows it. A catalog update sends the `currentEntityVersion` that was read. A table properties update sends an `assert-table-uuid` requirement. A conflict is shown as "changed since you loaded it, reload".
  - An e2e check for every object type does a round trip: write through our API, read back through Polaris directly, and compare. It also covers a delete, which must be gone from Polaris.

## Constraints

- Polaris 1.8.0 is deployed (`platform/21-polaris`).
- The backend reaches Polaris with the credential in `bootstrap/configs/catalog_settings.py`: the root principal, scope `PRINCIPAL_ROLE:ALL`. `docs/agents/known-follow-ups.md` already notes that this should become a scoped principal. This project keeps that credential. A write through our API therefore has Polaris root power, and the console's only guard is the Keycloak login gate in front of `/console/`.
- Today PyIceberg reaches only the catalogs listed in `CatalogSettings.names` (default `iceberg`). The catalog context must work with any catalog that Polaris returns, including ones created through the new pages.
- PyIceberg does not cover the Polaris management API or generic tables, so those adapters need a plain HTTP client.
- `create_app` lives inside `table_maintenance`'s web adapter today. A second context's routers must be mounted without the two contexts importing each other. The builder decides where the app is put together; `bootstrap` is the only place allowed to see both contexts.
- The console uses the existing stack and look: React, TanStack Query, shadcn components, and the rules in `src/data-platform/frontend/CLAUDE.md`.
- The work is done TDD, with every commit passing `task pre-pr`. The wave 25 bootstrap, validate and e2e scripts must still pass on the cluster at the end.

## Left to the builder

- The domain model inside each aggregate: which fields, which value objects, and how a nested namespace path is represented.
- How generic tables and Iceberg tables share the namespace page. The rows can be one list with a type column or two lists, as long as the pattern is consistent.
- API route shapes under `/v1`, and the DTOs, following the naming rules.
- How the Polaris adapters get and refresh tokens. Reusing the existing catalog settings is expected.
- How e2e or validate covers the new pages and routes.
