# Data Platform Console — Design

The data platform console is a web UI for table owners, sitting in front of the table-maintenance API. **The first version answers one owner's question: what is this Iceberg table, how big and how fresh is it, and is the platform keeping it healthy?** It starts as the table page of the "GitHub for Data" vision: a table plays the role a repository plays on GitHub. The tabs, the health view and the commit history are the parts that later features (branches, tags, previews) attach to.

## Intent

A table owner opens one table to learn three things: its shape (schema, partition spec, properties), its size and write activity (rows, files, bytes, commits), and what maintenance the platform has run on it and whether it helped. Today the owner can only get this from Trino queries, the Temporal UI and raw API calls. The console puts it on one page.

Goals:

- One table page with tabs, plus a table list page to find the table.
- Show Iceberg metadata the API does not expose today, through a new read-only API.
- Three product views on the Overview tab: **Health**, **Storage**, **Freshness & activity**.
- Let the owner act where an action already exists in the API: run maintenance now, pause/resume, edit the table's maintenance settings.

Non-goals (first version):

- Authentication, authorization, multi-tenancy. The console is reachable only through the local cluster gateway, like the API itself (see the known follow-up "No auth on the API").
- Data preview, time-travel queries, notifications or SLAs (they need Trino or new infrastructure).
- Branches, tags, rollback.
- Partition explorer and schema-evolution history (next after this version).
- Editing presets, discovery rules or discovery settings. The console shows the preset a table came from; it does not manage presets.

Anti-goals: the console must never disagree with the scheduler. If the Health view says an operation is not due, the scheduler must not run it on its next plan, and the other way round. A console that invents its own health score would break this.

## Users and pages

The only user is a **table owner**. There is no login; every visitor sees every table.

### Table list

The entry page lists the tables the control plane knows (`GET /v1/tables`): fully qualified name (`catalog.namespace.table`), status (`ACTIVE`, `PAUSED`, `EXCLUDED`, `DROPPED`), selection (rule or manual), source preset. A status filter and a text search over the name work on the loaded list in the browser. The list does not load Iceberg metadata per row: one metadata scan per table would make the list as slow as the number of tables.

### Table page

A header sits above every tab. It shows the table name, its status badge, the preset and rule that enrolled it, and two actions: **Run maintenance** (pick operations, `POST /v1/tables/{uuid}/maintenance`) and **Pause** / **Resume**. Below the name runs one row of summary numbers from the current snapshot: rows, data files, total bytes, average data-file size, snapshot count, time since the last commit.

The tabs are:

| Tab | Content | Source |
| --- | --- | --- |
| Overview | Health, Storage, Freshness & activity (below); schema; partition spec; last 5 commits; last maintenance run | new read API + existing API |
| Commits | Iceberg snapshots, newest first: commit time, operation (`append`, `overwrite`, `replace`, `delete`), rows and data files added / removed, writer. A row expands to the snapshot id, parent id and the full snapshot summary. | new read API |
| Maintenance | Runs of this table (`GET /v1/tables/{uuid}/table-maintenance-runs`): trigger, status, start, duration; per operation its attempts, result, error and metrics. A run links to its Temporal execution by `execution_ref`. | existing API |
| Properties | Iceberg table properties as key/value, format version, location. Read-only. | new read API |
| Settings | The table's maintenance settings (thresholds, cooldowns, scope), editable (`PUT /v1/tables/{uuid}/settings`), with **Reset to preset**. | existing API |

**Reset to preset is a console action, not a new backend use case.** It reads the source preset (`GET /v1/table-maintenance-presets/{id}`) and writes its settings with the existing `PUT`. If the table has no source preset the button is hidden.

## The three Overview views

### Health

**Health is the scheduler's own evaluation, shown line by line.** One line per maintenance operation (`rewrite_data_files`, `rewrite_manifests`, `expire_snapshots`, `remove_orphan_files`) states whether the operation is due now and why, in the scheduler's terms: "12 reducible files, threshold 5", "2 small manifests, threshold 10", "16 snapshots past retention", "disabled", or "in cooldown until 2026-11-01 09:12". A due line carries a **Run now** button that triggers that one operation manually.

This requires one source of truth. Today `plan_scheduled_maintenance` (`application/domain/service/table/`) returns only the operations it plans. It is refactored so that a single evaluation produces, per operation, the verdict (due / not due / disabled / cooldown), the measured value, the threshold and the next eligible time; the scheduled plan is derived from that evaluation (the due operations, with their filters and procedure args). The Health use case returns the evaluation itself. Planning behaviour must not change: every existing planner test keeps passing unchanged.

What each line measures follows the planner's own check:

| Operation | Measured value | Threshold | Notes |
| --- | --- | --- | --- |
| `rewrite_data_files` | reducible files (summed over the table for `scope=table`; for `scope=partition`, the number of qualifying partitions and their summed reducible files) | `min_reducible_files` | target file size shown with its source (settings or table property) |
| `rewrite_manifests` | manifests below the small-manifest threshold | `min_small_manifests` | the byte threshold shown with its source (settings, property or 8 MiB default) |
| `expire_snapshots` | snapshots that would expire (beyond the newest `retain_last`, older than `older_than`, not current) | due when at least 1 | the planner's `any` becomes a count; due iff count ≥ 1 |
| `remove_orphan_files` | none | none | due whenever enabled and out of cooldown |

A cooldown verdict carries the next eligible time (`last_attempt_at` plus the effective cooldown, which includes failure backoff). A disabled operation has no next time.

**A table the scheduler skips gets a table-level verdict instead of lying lines.** When the table is `PAUSED`, `EXCLUDED` or `DROPPED`, Health returns `scheduled: false` with that reason, and the per-operation lines are computed as they would be if the table were active, labelled "would be due when resumed". A table with no settings returns `scheduled: false`, reason `no_settings`, and no lines. This mirrors the skip reasons of `plan_table_maintenance`.

**Run now is a manual run.** It calls the existing `POST /v1/tables/{uuid}/maintenance` with that one operation, which `plan_manual_maintenance` plans on the whole table with no threshold check and no partition filters. The confirmation dialog says so ("runs on the whole table, ignoring thresholds"), so the button never promises the scheduler's partition scope.

One extra line has no operation behind it: **delete files**, the count of position and equality delete files in the current snapshot. CDC writes accumulate them and they slow reads. The line is informational; no current operation is gated on it.

### Storage

Storage splits bytes into what the current snapshot references and what only older snapshots reference. The second figure is the cost of keeping time travel, and `expire_snapshots` is what reduces it. Both come from Iceberg metadata: current files from the current snapshot, all referenced files from the table's all-files metadata (PyIceberg 0.11 `inspect.all_files`). Under the bar, the view sums what maintenance reclaimed over the last 30 days from the operation metrics already stored on succeeded attempts. The keys are the ones the Iceberg procedures return and the e2e run recorded:

| Figure | Metric key (operation) |
| --- | --- |
| data files rewritten → added | `rewritten_data_files_count` → `added_data_files_count` (`rewrite_data_files`) |
| bytes rewritten | `rewritten_bytes_count` (`rewrite_data_files`) |
| manifests rewritten → added | `rewritten_manifests_count` → `added_manifests_count` (`rewrite_manifests`) |
| snapshots expired | `deleted_manifest_lists_count` (`expire_snapshots`; one manifest list per snapshot) |
| files deleted by expiry | `deleted_data_files_count`, `deleted_manifest_files_count`, `deleted_position_delete_files_count`, `deleted_equality_delete_files_count` (`expire_snapshots`) |

An attempt recorded as `{"completed_without_callback": 1}` has no procedure metrics and adds nothing; the view states how many such attempts the window holds. The 30-day window needs a new runs-repository query by table and start time; the existing list endpoint (latest N) is not reused for it.

**Storage loads on its own.** `inspect.all_files` reads the manifests of every snapshot, which on a CDC table with many snapshots costs more than the scheduler's single-snapshot scan. The Overview renders header, Health and Freshness first and fills Storage when its call returns, with its own loading and error state. A cache is a later concern.

**Orphan-file bytes are not shown.** Measuring them means listing the whole table location in object storage, which is the expensive part of `remove_orphan_files` itself. `remove_orphan_files` currently reports empty metrics, so the 30-day sum has no orphan figure either.

### Freshness & activity

The view shows when the last commit landed and who wrote it, a bar chart of commits per hour over the last 24 hours coloured by operation, and the writer mix over the same window. It displays only; staleness thresholds and alerts belong to the later notifications work.

**The writer is derived from the snapshot summary alone.** A summary with keys starting `kafka.connect.` is "Kafka Connect"; a summary carrying `spark.app.id` is "Spark"; anything else is "unknown". On this platform Spark only writes through table maintenance, but the console does not claim that: maintenance runs record no snapshot ids, so a snapshot cannot be tied to a run, and recording them (runtime, callback, schema) is out of scope. The mapping lives in one place in the backend so the Commits tab and this view agree.

The chart asks for `commits?since=<now − 24h>`. If the window holds more commits than the endpoint's maximum `limit`, the response says it was truncated and the view shows the count as "≥ N".

## Read API

The new endpoints are read-only and sit under the existing table resource:

| Endpoint | Returns |
| --- | --- |
| `GET /v1/tables/{uuid}/metadata` | summary numbers of the header, schema, partition specs, properties, format version, location |
| `GET /v1/tables/{uuid}/commits?limit=&since=` | snapshots newest first with operation, added / removed rows and files, writer, ids, full summary; `limit` defaults to 100, at most 1000; `since` is ISO-8601; the response carries `truncated` |
| `GET /v1/tables/{uuid}/health` | the per-operation evaluation and the delete-file line |
| `GET /v1/tables/{uuid}/storage` | current and only-old-snapshot bytes and file counts, the 30-day reclaimed sums |

Each endpoint is its own use case under `application/service/table/` with its own inbound port, and reads Iceberg through the outbound `ReadTableMetadataGateway` (extended, or a sibling `Read…Gateway` under `port/outbound/table/`; the builder chooses, within the naming rules). Freshness & activity is computed in the browser from `commits`. **There is no cache in the first version**: each call loads table metadata from the catalog, which is what one plan already costs the scheduler. An unknown table is 404; a table registered in the DB but missing in the catalog (`not_found`) returns 404 from the metadata endpoints with a body that says so, and the page shows the DB fields with a "not in catalog" notice.

All backend rules in `CLAUDE.md` apply: the aggregate axis, ports that speak intent (no `iceberg`, `pyiceberg`, `snapshot` is fine), use-case outputs as application dataclasses, API DTOs with `ApiResponse` suffixes, TDD, and the four checks before every commit.

## How it gets made

These are the calls made for the user, who accepted them:

- **Stack**: React with TypeScript, built with Vite, as a single-page app. Tests with Vitest and Testing Library.
- **Location**: `src/console/`, because the console serves the whole data platform, not only table maintenance.
- **Packaging**: one image (`console`) serving the built files from nginx. The image is built locally and loaded into minikube by `platform/25-lakehouse-control-plane/build.sh`, like the backend and Spark images.
- **Deployment**: a `console` Deployment and Service in the `table-maintenance` Helm chart (wave 25, namespace `lakehouse-control-plane`), plus an `HTTPRoute` on `platform-gateway`.

The routing needs care. `platform-gateway` (`platform/22-polaris-routes/gateway.yaml`) admits routes only from `lakehouse-catalog`, and Polaris owns it through a catch-all route on `/`. The console therefore lives under the path prefix `/console`: its `HTTPRoute` matches `PathPrefix /console`, which is more specific than Polaris's catch-all, and the gateway's `allowedRoutes` selector is widened to admit `lakehouse-control-plane` (a `matchExpressions` `In` over `kubernetes.io/metadata.name` with both namespaces; the Polaris route has no hostnames or path match, so nothing else conflicts). That edit lives in wave 22 and its `validate.sh` keeps passing; wave 25 owns the console route. Inside the console pod, nginx serves the app at `/console/` and proxies `/console/api/` to `table-maintenance-api.lakehouse-control-plane.svc.cluster.local:8000`, so the browser talks to one origin and the API needs no CORS. The owner opens it with the gateway port-forward already documented in `platform/22-polaris-routes/README.md` and browses to `http://localhost:8080/console/`.

`validate.sh` checks the console Deployment is ready and that the gateway answers `/console/` and `/console/api/v1/tables`. `e2e.sh` additionally reads `metadata`, `commits`, `health` and `storage` of `tm_e2e_orders` through the gateway after the maintenance runs and asserts they agree with what it measured (file and snapshot counts after maintenance).

## Calls the builder makes

- Visual design, component library and styling, as long as the layout above holds and pages work at laptop width.
- Routing, data-fetching and charting libraries; prefer few dependencies.
- The exact shape of the evaluation type and the response DTOs.
- Whether the Run maintenance dialog defaults to all operations or to the due ones.
- UI copy language: English (the docs, API and operation names are English).

## References

- [Apache Iceberg table spec: snapshots and summaries](https://iceberg.apache.org/spec/#snapshots)
- [Apache Iceberg metadata tables (`all_files`, `snapshots`)](https://iceberg.apache.org/docs/latest/spark-queries/#inspecting-tables)
- [PyIceberg inspect API](https://py.iceberg.apache.org/api/#inspecting-tables)
- [Gateway API HTTPRoute path matching](https://gateway-api.sigs.k8s.io/reference/spec/#httppathmatch)
- `docs/superpowers/specs/2026-10-29-backend-architecture-conformance-design.md` (backend layout rules)
