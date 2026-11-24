# KCL-104 inventory: cluster verification checks to move into pytest e2e scenarios

Written 2026-11-24 from the plans in `docs/superpowers/plans/`, the Linear notes of the 2026-11-22 manual run
(`.superpowers/kcl-104-inventory/linear-notes.md`), the KCL-104 description, and the code at `main` (def88f86).
Nothing was run on a cluster.

## Reading guide

* Class: `AUTO-critical` = API-only, seconds to about a minute (up to ~2 min with scan/reconcile waits that the call itself triggers).
  `AUTO-full` = needs a scrape/schedule wait or a worker restart. `MANUAL` = a person judges it, it is a one-off, it needs MySQL/Trino, or it is
  infrastructure validation that other tools already own (reason tagged: `[visual]`, `[superseded]`, `[infra]`, `[cdc]`, `[logs]`, `[deploy-change]`).
  `KCL-105` = maintenance run / compaction / queue / reconciliation timing; not counted here.
* API prefix is `/v1` (what the e2e pod calls in-cluster). E2E principal = `tm-e2e` (service_admin + CATALOG_MANAGE_CONTENT on `iceberg`).
* "Own catalog" = a catalog the scenario creates through `POST /v1/catalogs` (as `test_catalog_round_trip.py` does, storage under
  `s3://tm-e2e-catalogs/<name>`, name matching `OwnedNames.CATALOG`). Reason: discovery schedules, scanned catalogs and "catalog falls back to the defaults"
  are per catalog, and `iceberg` is shared with the other full scenarios, so "the schedule is deleted after detach" or "the catalog is no longer scanned" only hold in a catalog nobody else attaches in.
  Needs: a per-catalog PyIceberg `Catalog` fixture (same settings as the `iceberg` fixture, `warehouse=<own catalog>`) and a `ManagedTable`-like helper that takes a catalog name (today it is hard-wired to `settings.catalog`).
* Already covered = what `e2e/test_*.py` asserts today:
  * `test_catalog_round_trip.py`: catalog API round trip (catalog/namespace/table, properties, Polaris comparison).
  * `test_platform_answers.py`: platform answers.
  * `test_manual_maintenance.py`: effective policies by uuid for a table with its own maintenance policy + namespace discovery policy; `pa-`/`da-`/`mp-`/`dp-`/`dr-`/`mr-`/`rc-` ids; catalog API metadata + commits newest first vs PyIceberg; reconcile-now record; four manual runs.
  * `test_scheduled_partition_compaction.py`: discovery schedule of `iceberg` exists, `scanned-catalogs` shows `iceberg` with `failure: null`, namespace attach manages the table, effective policies by uuid, `metrics/current` `data_files` not null.
  * `ManagedTable` cleanup implicitly proves detach unmanages the table and stops its reconciliation (a timeout fails the test), but asserts nothing else about detach.

## Plan wording that differs from the code today

| plan says | code does now |
|---|---|
| reconciliation workflow receives `stopped` on detach | the signal is `stop` (`TableReconciliationSignal.STOP`) |
| `GET /v1/tables/{uuid}/commits` returns `schema_id` 0, 1, 1 | list is newest first: `1, 1, 0` |
| `/api/v1/discovery-rules`, `/v1/discovery-rules/catalogs` | gone (404); discovery policies `/v1/discovery-policies`, `/v1/scanned-catalogs` |
| `/mappings` routes and the two `applicable-policy` routes | gone (404); `/v1/maintenance-policies/{name}/attachments` (PUT answers `{id: pa-...}`, DELETE by `pa-` id), `/v1/effective-policies?catalog=&namespace=&table=` and `/v1/tables/{uuid}/effective-policies` |
| gateway path `/api/v1` | in-cluster the API answers at `/v1` |
| "17 samples" per table in `/v1/table-metrics` | still true (1 info, 1 observed timestamp, 4 `iceberg_table_files`, 8 single-value families, 3 manifest entries); route is hidden from OpenAPI but exists |
| schema v1 changes `added 1, renamed 1, type_changed 1, nullability_changed 1` | response also carries `removed` and `doc_changed` (both 0); `changes` is `null` for the first version |
| discovery scan "within a minute" | attach/detach/policy update rescans at once (`apply_discovery_change`, ~2 s in the 2026-11-22 run); the schedule itself fires every `discovery_interval_seconds` = 600 s |
| default policies: PUT/DELETE on `default` give 409 | true for the default *discovery* policy (`ConflictError`). The default *maintenance* policy has no such guard on PUT: it can be edited and gets a new version, so e2e must never edit it and must not assume its content is version 1 |
| tables created through Trino (`trino_sql`) | every e2e table is created with PyIceberg or the catalog API |
| discovery condition on `catalog` | conditions are `namespace` and `table_name` only; catalog is decided by the attachment target |
| table status values | `managed` / `unmanaged` only |

## Special needs, in one place

* **Make a catalog unreadable (KCL-71 check 6/7, KCL-98 403).** On the scenario's own catalog, with the e2e principal (service_admin):
  1. `GET /api/management/v1/catalogs/{c}/catalog-roles/catalog_admin/grants` to note the grants; confirm which catalog role the platform's principal reaches the catalog through (`GET /principals/{p}/principal-roles`, then `.../principal-roles/{role}/catalog-roles/{c}`). On an API-created catalog this is `catalog_admin` granted to `service_admin`.
  2. Revoke only `CATALOG_MANAGE_CONTENT` and `CATALOG_MANAGE_METADATA` on that role: `POST /api/management/v1/catalogs/{c}/catalog-roles/catalog_admin/grants` with `{"grant": {"type": "catalog", "privilege": "CATALOG_MANAGE_CONTENT"}}` is the revoke call in the 2026-11-22 run; re-grant is `PUT` on the same path. Confirm both against the Polaris 1.8 management spec when writing it. Keep `CATALOG_MANAGE_ACCESS` so the grant can be added back.
  3. Cleanup order (push on the CleanupStack before the revoke): `PUT` both grants back, detach policies, delete policies, `drop_catalog`.
  4. Never remove the platform's only role. `sweep_leftovers`/`drop_catalog` do not re-grant today, so add "re-grant before dropping" to the sweep for e2e catalogs, or an interrupted run leaves a catalog Polaris cannot empty (the 2026-11-22 `kcl71_noaccess` problem).
* **Worker restart (KCL-71 check 7).** The e2e pod has `automountServiceAccountToken: false` and the default ServiceAccount: no Kubernetes access at all. It would need:
  * a ServiceAccount (for example `table-maintenance-e2e`), a Role and RoleBinding in namespace `lakehouse-control-plane` with core `pods` verbs `get, list, watch, delete` (delete the pod labelled as the worker; the Deployment, `replicas: 1`, recreates it); or `apps` `deployments` verbs `get, patch` (a rollout restart is a patch of the pod template annotation) plus `pods` `get, list` to wait;
  * `serviceAccountName` and `automountServiceAccountToken: true` in `platform/25-lakehouse-control-plane/e2e/pod.yaml`; `kubernetes` client library added to `requirements-e2e.txt` if not already there.
  * Time: worker `terminationGracePeriodSeconds` is 90, then start, then ~8 s until the schedule sync finishes; poll with a ~240 s bound. The restart interrupts anything the worker is doing (Temporal retries); acceptable on dev, say so in the scenario doc.
* **Prometheus trends (KCL-96).** Prometheus scrapes `/v1/table-metrics` every 30 s, retention 6 h. Metrics are saved only when a plan runs, so trigger it with `POST /v1/tables/{uuid}/reconcile`; a new step shows in `GET /v1/tables/{uuid}/metrics?range=1h` after one or two scrapes (poll up to ~150 s). The e2e pod only needs the API. The "Prometheus down" half (scale `table-metrics` Prometheus to 0) needs a Role in namespace `table-metrics`: `apps` `deployments/scale` verbs `get, update, patch` (and `deployments` `get`); undo = scale back to 1, also in the sweep.
* **Rescan instead of waiting.** Any attach, detach or discovery-policy update rescans the affected catalogs (`apply_discovery_change`, best effort) and records a failed scan. So "recorded `cannot_access`" can be provoked in seconds by updating the attached policy (new version) after the revoke, instead of waiting for the 600 s schedule. If the first real run shows the failure is recorded only by the scheduled scan, move check 1.8 to `full`.

---

## Source 1. `2026-11-21-discovery-policy.md`, Task 16 (KCL-71)

2026-11-22 manual result: checks 1-7 passed (linear-notes). The older `2026-11-20-discovery-policy.md` Task 16 is in Source 7.

| # | check (plain words) | how to verify (API calls, expected answers) | code today | class | scenario group suggestion |
|---|---|---|---|---|---|
| 1.1 | The default discovery policy has no rules, manages nothing, and cannot be changed or deleted | `GET /v1/discovery-policies/default`: `is_default: true`, `rules: []`, `no_match_outcome: "unmanage"`, `id` prefixed `dp-`. `PUT /v1/discovery-policies/default` (with its `version`) and `DELETE` both 409 | `UpdateTableDiscoveryPolicyService` / delete service raise `ConflictError` for the default; handler maps to 409. Matches plan | AUTO-critical | `test_discovery_policies.py` |
| 1.2 | Attaching a managing policy to a namespace builds the catalog's discovery schedule and scans; the namespace's tables become managed with the deciding policy, version and rule recorded | Own catalog: namespace + 3 tables (PyIceberg), create policy (`manage` on `table_name` glob, no-match `unmanage`), `PUT /v1/discovery-policies/{p}/attachments {"target":{"type":"namespace","path":[c,ns]}}` -> `{id: da-...}`. Poll (<= 60 s): Temporal `get_schedule_handle("table-discovery:catalog=<c>").describe()` succeeds, not paused; an ad hoc workflow id starting `table-discovery:catalog=<c>` and containing `trigger=policy-changed` completed; `GET /v1/scanned-catalogs` lists `<c>` with `failure: null`, `last_discovered_at` set; `GET /v1/tables?status=managed` shows the 3 tables with `matched_policy_id` = the `dp-` id, `matched_policy_version` 1, `matched_rule_id` = `policy.rules[0].id` (`dr-`). A table in a second, unattached namespace is `unmanaged` with `matched_policy_id` = default's id, `matched_rule_id` null | attach service -> `apply_discovery_change` rescans + syncs schedules; schedule id `table-discovery:catalog=<c>`; ad hoc id `table-discovery:catalog=<c>[:namespace=<n>]:trigger=policy-changed:change=<id>`; `TableApiResponse` has `matched_rule_id`, `matched_policy_id`, `matched_policy_version`. Partly covered by `test_scheduled_partition_compaction.py` (schedule, `failure: null`, managed) but not the matched_* fields, the policy-changed run or the unattached namespace | AUTO-critical | `test_discovery_lifecycle.py` (own catalog); new part only |
| 1.3 | The attachment nearest to the table wins (default attached on one table unmanages only that table) | After 1.2: `PUT /v1/discovery-policies/default/attachments {"target":{"type":"table","path":[c,ns,t1]}}`. Poll (<= 60 s): `t1` is `unmanaged` with `matched_policy_id` = default's id; the other two stay `managed`; `GET /v1/discovery-policies/default/attachments` lists it | attaching the default is allowed; table target resolved to uuid via the catalog | AUTO-critical | `test_discovery_lifecycle.py` |
| 1.4 | Detaching unmanages the tables, sends their reconciliations `stop`, deletes the catalog's schedule and drops it from scanned catalogs | `DELETE /v1/discovery-policies/{p}/attachments/{da-id}` -> 204 (and the table-level default attachment). Poll (<= 90 s): tables `unmanaged`; each `table-reconciliation:table-uuid=<uuid>` workflow history has a `stop` signal and is not running; `describe()` of the schedule raises not-found; `<c>` absent from `GET /v1/scanned-catalogs` (do not assert the whole list empty) | signal is `stop`, not `stopped`; `SyncDiscoverySchedulesTemporalGateway` deletes schedules of catalogs no longer scanned after their final scan | AUTO-critical | `test_discovery_lifecycle.py` |
| 1.5 | Attaching to an empty namespace works | `POST /v1/catalogs/{c}/namespaces` (empty), `PUT .../attachments` -> 200 with `id`; `GET /v1/discovery-policies/{p}/attachments` lists it | namespace/catalog may be empty; target must exist | AUTO-critical | `test_discovery_policies.py` |
| 1.6 | Attaching to a namespace or catalog that does not exist is 404 and nothing is stored | `PUT` with `path:[c,"no_such_ns"]` -> 404 with a `detail`; `path:["no_such_catalog"]` -> 404; attachments list unchanged; no schedule `table-discovery:catalog=no_such_catalog` | `NotFoundError` / `CatalogNotFoundError` -> 404; a refused attach neither rescans nor syncs | AUTO-critical | `test_discovery_policies.py` |
| 1.7 | Attaching in a catalog the platform cannot read is 403 with the reason | Own catalog, grants revoked (see Special needs). `PUT .../attachments` on a namespace -> 403, non-empty `detail`; attachments list unchanged | `CatalogAccessDeniedError` -> 403 | AUTO-critical | `test_discovery_unreadable_catalog.py` (needs revoke POST / grant PUT on `catalog_admin`, cleanup re-grants before drop) |
| 1.8 | A catalog that was readable and later is not is recorded `cannot_access`, and the scanned-catalogs list shows the failure | Re-grant, attach a managing policy, poll until `<c>` shows `failure: null`, `last_discovered_at` set; revoke; update the attached policy (`PUT /v1/discovery-policies/{p}` with current `version`) to force a rescan; poll (<= 90 s) until `<c>` has `failure.reason == "cannot_access"`, a `detail`, `failed_at`, and `last_discovered_at` still the earlier value. Re-grant, update the policy again, see `failure: null`. Fallback: wait for the scheduled scan (<= 600 s) and class it `full` | `sync_discovered_tables` records `CatalogScanFailure(reason=cannot_access)`; `ScannedCatalogApiResponse.failure` null unless the failed scan is newer than the last completed one | AUTO-critical (AUTO-full if the rescan does not record it) | `test_discovery_unreadable_catalog.py` |
| 1.9 | Console shows the cannot-access banner on the list page and "discovery cannot read this catalog" on a table page | -- | UI copy and placement judged by a person; stories exist | MANUAL [visual] | story tests |
| 1.10 | After a worker restart the deleted discovery schedule is rebuilt | Own catalog with a managing policy attached; `get_schedule_handle(id).delete()`, wait until `describe()` raises; restart the worker (pod delete, see Special needs); poll (<= ~240 s, 5 s interval) until `describe()` succeeds and is not paused | worker start syncs schedules; readiness does not wait for the sync (~8 s after ready) | AUTO-full | `test_worker_restart_schedules.py`; needs e2e ServiceAccount + Role (`pods` get,list,watch,delete in `lakehouse-control-plane`) and pod.yaml changes |
| 1.11 | Console flows: sidebar entry, create policy, add/reorder rules, save -> v2, v1 readable, "what changed" on v2, attach/detach, scan state per row, default read-only, `/discovery-rules` redirect, Overview names policy/version/rule, no sideways scroll at 390 px | -- | layout, copy, redirects and responsive behaviour judged by a person at two widths; the API half is 1.12 | MANUAL [visual] | story tests |
| 1.12 | API half of 1.11: saving makes version 2 and version 1 stays readable; a stale version is 409; rule ids survive a reorder; deleting an attached policy is 409 | `POST /v1/discovery-policies` (rules without ids get `dr-`), `PUT /v1/discovery-policies/{p}` with `version: 1`, rules reordered/extended (kept rules send their ids) -> `version` 2, kept rules keep ids; `GET .../versions/1` equals the original; `PUT` again with `version: 1` -> 409; attach then `DELETE /v1/discovery-policies/{p}` -> 409; detach, delete -> 204, `GET` -> 404. "What each version changed" has no API (console only) | routes `/{name}`, `/{name}/versions/{version}` exist; stale -> `ConflictError`, unknown rule id -> 422 | AUTO-critical | `test_discovery_policies.py` |
| 1.13 | `e2e.sh` passes; `gates:pre-pr` recorded | -- | `e2e.sh` retired by KCL-102; the gate is not a cluster behaviour | MANUAL [superseded] | none |
| 1.14 | Fresh rebuild has no discovery schedule and `scanned-catalogs` is `{"catalogs": []}` before any attach | -- | fresh-cluster state; e2e cannot assume an empty shared platform; `apps:validate` owns the rebuild; per-catalog equivalents are 1.2 and 1.4 | MANUAL [infra] | `apps:validate` |

## Source 2. `2026-11-21-effective-policies.md`, Task 6 (KCL-98)

2026-11-22 manual result: all passed. Existing e2e covers the uuid route for a table with its own maintenance policy and a namespace discovery policy (kind order, `policy_name`, `attachment_id`, `target`).

| # | check (plain words) | how to verify (API calls, expected answers) | code today | class | scenario group suggestion |
|---|---|---|---|---|---|
| 2.1 | A table with its own maintenance policy shows it with source `table`; its sibling shows the namespace's policy; both show the namespace's discovery policy; every entry carries its `pa-`/`da-` attachment id | Own catalog, namespace `ns`, tables `a`, `b`: policies `m-ns`, `m-a` (dry-run), `d-ns`; attach `m-ns`, `d-ns` to the namespace, `m-a` to table `a` (`path:[c,ns,a]`). `GET /v1/effective-policies?catalog=c&namespace=ns&table=a` and `...table=b`: `policies` = `[maintenance, discovery]`; `a`: `policy_name m-a`, `target.type table`, `attachment_id` = its `pa-` id; `b`: `m-ns`, `target.type namespace`, path `[c, ns]`; discovery for both `d-ns` from the namespace with the `da-` id; `version` = latest. With discovery managing the tables, `GET /v1/tables/{uuid}/effective-policies` for `b` equals the by-location answer. By-location needs no managed table | `effective_policies_router.py`; entries `MaintenanceEffectivePolicyApiResponse` (`dry_run`) and `DiscoveryEffectivePolicyApiResponse` (`no_match_outcome`). Matches plan | AUTO-critical | `test_effective_policies.py` (own-policy by uuid already covered by `test_manual_maintenance.py` and `test_scheduled_partition_compaction.py`; sibling and by-location are new) |
| 2.2 | Detaching the table's attachment by its `pa-` id falls back to the namespace's policy | `DELETE /v1/maintenance-policies/m-a/attachments/{pa-id}` -> 204; same query for `a` now names `m-ns` from the namespace; DELETE with another policy's `pa-` id -> 404; malformed id -> 422; re-PUT without detach keeps the id | detach by id: 204 / 404 / 422 | AUTO-critical | `test_effective_policies.py` |
| 2.3 | A catalog-only query (nothing attached at catalog level) gives both platform defaults with no attachment | `?catalog=c` in an own catalog: maintenance `policy_name "default"`, discovery `"default"`, `target: null`, `attachment_id: null`; nested namespace is dot-joined (`ns.child`) | no attachment -> default policy | AUTO-critical | `test_effective_policies.py` |
| 2.4 | The removed routes answer 404 | `GET/PUT/DELETE /v1/maintenance-policies/{real}/mappings`, `GET /v1/tables/{real uuid}/applicable-policy`, `GET /v1/applicable-policy?catalog=c` -> 404 (not 405) | none registered | AUTO-critical | `test_removed_routes.py` |
| 2.5 | A place that does not exist is 404; an unreadable catalog is 403; a table maintenance has no record of is answered by location | `?catalog=c&namespace=nope`, `?catalog=nope`, `...&table=nope` -> 404; `GET /v1/tables/{random uuid}/effective-policies` -> 404; unreadable own catalog (1.7 setup) `?catalog=c&namespace=ns` -> 403; unrecorded table `a` in 2.1 answers by location | plan rulings (not in Task 6's cluster list, cheap on the same API); handlers map NotFound -> 404, `CatalogAccessDeniedError` -> 403 | AUTO-critical | 404 half `test_effective_policies.py`; 403 half `test_discovery_unreadable_catalog.py` |
| 2.6 | Console "Policies" panel (Attach/Replace/Detach, origin text) | -- | not in Task 6's list; story-tested | MANUAL [visual] | story tests |
| 2.7 | A maintenance attachment whose target was dropped lists as `orphaned` and can still be detached | `GET /v1/maintenance-policies/m-a/attachments` after dropping table `a`: `orphaned: true`; DELETE -> 204 | unit-tested only today (extra, ~3 s) | AUTO-critical | `test_effective_policies.py` |
| 2.8 | Other removed routes answer 404 | `GET /v1/discovery-rules`, `/v1/discovery-rules/catalogs`, `/v1/compaction-rounds`, `/v1/tables/{real uuid}/health`, `/v1/tables/{real uuid}/storage` -> 404 | absent in code; only unit tests and `validate.sh` check this today (extra, ~2 s) | AUTO-critical | `test_removed_routes.py` |

## Source 3. `2026-11-20-maintenance-policy-target-state.md`, Task 9 (KCL-91)

| # | check (plain words) | how to verify (API calls, expected answers) | code today | class | scenario group suggestion |
|---|---|---|---|---|---|
| 3.1 | Rebuild and `apps:validate` exit 0 | -- | deployment validation | MANUAL [infra] | none |
| 3.2 | The default maintenance policy has the target-state shape and values | `GET /v1/maintenance-policies/default`: top-level `description`, `on {schedule {every_seconds 3600}, catalog_commit {debounce_seconds 300}}`, `dry_run false`, `rewrite_data_files {target {reducible_files {at_most 5}, per "partition"}, options {min_input_files 2, partial_progress_enabled true}}`, `rewrite_manifests {target {small_manifests {at_most 5}}}`, `expire_snapshots {target {min_snapshots_to_keep 10, max_snapshot_age_seconds 86400}}`, `remove_orphan_files {target {older_than_seconds 259200}}`; `id` `mp-`, `is_default`, `version`; no `operations`/`priority`/`trigger_policy` keys. Assert the shape always, the values only when `version == 1` (the default can be edited on a long-lived cluster) | matches `MaintenancePolicyContent.platform_default()` | AUTO-critical | `test_maintenance_policies.py` |
| 3.3 | Platform settings list the four cooldowns | `GET /v1/platform-settings`: items `maintenance_rewrite_data_files_cooldown_seconds`, `maintenance_rewrite_manifests_cooldown_seconds`, `maintenance_expire_snapshots_cooldown_seconds`, `maintenance_remove_orphan_files_interval_seconds` exist as non-negative ints (do not pin the values: chart-owned); `discovery_interval_seconds` is an int | `get_platform_settings.py` | AUTO-critical | `test_maintenance_policies.py` |
| 3.4 | A policy with an option the platform owns is refused | `POST /v1/maintenance-policies` with `expire_snapshots.options.retain_last` -> 422; unknown option on another operation -> 422; policy not in the list afterwards | `ExpireSnapshotsOptions` knows only `max_concurrent_deletes`, `stream_results`; invariant violation -> 422 | AUTO-critical | `test_maintenance_policies.py` |
| 3.5 | A table that becomes managed gets a first reconciliation recorded as `table_managed`; later discovery scans add no record | Own catalog + dry-run managed table (maintenance policy attached first, discovery policy second, as `ManagedTable.create` orders them); poll `GET /v1/tables/{uuid}/reconciliations` for a record with `wake_reasons == {"table_managed": 1}`. Note the count, force a rescan (update the discovery policy), wait ~20 s: count unchanged | `WakeReason` has no `discovery_scan`; `table_seen` plans nothing | AUTO-critical | `test_policy_records.py` (module-scoped managed table; the quiet wait costs ~20 s) |
| 3.6 | Attaching a policy records a `policy_changed` check naming the policy, version and target | Attach `kcl91` (dry-run, `on.schedule 300`, `catalog_commit 120`, one `rewrite_data_files` block) to the table's namespace: poll for a record with `wake_reasons` containing `policy_changed`, `policy_name`, `policy_id` `mp-`, `policy_version 1`, `policy_target == {type namespace, path [c, ns]}`, `policy_deleted false`, `dry_run true` | `TableReconciliationApiResponse` fields as listed | AUTO-critical | `test_policy_records.py` |
| 3.7 | 10 inserts within a minute give exactly one reconciliation ~120 s after the first commit counting the commits and a whole-table rewrite; the next at ~300 s with reason `schedule` | -- | commit-window debounce, schedule timing and a Spark run | KCL-105 | KCL-105 |
| 3.8 | Updating the policy to `every_seconds: 600` without `catalog_commit` records a `policy_changed` check at once | `PUT /v1/maintenance-policies/kcl91` with current `version` and `on: {schedule: {every_seconds: 600}}` -> `version 2`; poll for a record with `policy_changed`, `policy_version 2`. (Nothing from further inserts until ~600 s is timing: KCL-105) | update notifies each attached table | AUTO-critical | `test_policy_records.py` |
| 3.9 | Dropping `rewrite_data_files` and adding `expire_snapshots` shows `rewrite_data_files` as `off` in the next record and starts no rewrite | Update `kcl91` to only `expire_snapshots`; newest record: operation `rewrite_data_files` has `result == "off"`, `run_id` null; no new run with that operation. `dry_run: true` keeps it free of runs. (Expiry running once a snapshot is old enough: KCL-105) | `OperationResult.OFF = "off"` | AUTO-critical | `test_policy_records.py` |
| 3.10 | Console: policy editor keyboard-only, list shows "Checks" text, version page "Not in this policy", platform settings page shows cooldowns | -- | keyboard and wording judged by a person | MANUAL [visual] | story tests |
| 3.11 | `e2e.sh` passes, `gates:pre-pr` | -- | `e2e.sh` retired | MANUAL [superseded] | none |

## Source 4. `2026-11-20-overview-metric-trends.md`, Task 11 (KCL-96)

| # | check (plain words) | how to verify (API calls, expected answers) | code today | class | scenario group suggestion |
|---|---|---|---|---|---|
| 4.1 | Rebuild, `apps:validate` exits 0 including `26-table-metrics-prometheus` | -- | owned by `apps:validate` | MANUAL [infra] | none |
| 4.2 | A managed table's first reconcile makes `metrics/current` match the table and the exporter shows all 17 samples | Own managed table: empty first (counts 0, not null), then 3 appends and one delete, `POST /v1/tables/{uuid}/reconcile` (202), poll `GET /v1/tables/{uuid}/metrics/current` until `observed_at` set. `data_files` = PyIceberg live data files (`inspect.files()` content 0), `data_records` = sum of record counts, delete files and `snapshots` equal PyIceberg's. `GET /v1/table-metrics` text: 17 sample lines with `table_uuid="<uuid>"`, `iceberg_table_info{...} 1`, `iceberg_table_files{content="data"}` = API `data_files`. Unmanaged uuid -> 200 with both fields null; unknown uuid -> 404 | `get_table_current_metrics`; `table_metrics_router.py` + `table_metrics_exposition.py`. The plan used the CDC table `iceberg.inventory.orders`, which e2e must not touch; use an owned table. Existing coverage is only "`data_files` is not None" | AUTO-critical | `test_table_information.py` |
| 4.3 | Rows inserted through MySQL (CDC) move the metrics after the sink commits (up to 10 min), then the commit window checks the table | -- | needs MySQL, Debezium, Kafka and the sink: outside the e2e surfaces. Its table effect is 4.4 | MANUAL [cdc] | none |
| 4.4 | After new commits and a reconcile, `metrics/current` moves and within about a minute `GET .../metrics?range=1h` shows the step | Owned managed table: record counts, append with PyIceberg, `POST .../reconcile`, poll `metrics/current` until `data_records` grew; then poll (<= ~150 s, 10 s) `GET /v1/tables/{uuid}/metrics?range=1h`: `time_range "1h"`, ordered `points`; last non-null point equals the current counts and an earlier point is smaller or null (a seconds-old table may have null earlier points) | `get_table_metric_trends` (`range` 1h/3h/6h); scrape 30 s | AUTO-full | `test_metric_trends.py` (~2-3 min; no extra RBAC) |
| 4.5 | Console: six cards, six sections, range switch changes url and charts | -- | visual and interactive | MANUAL [visual] | story tests |
| 4.6 | After a manual compaction and reconcile the data files and reducible files drop | -- | needs a Spark compaction run | KCL-105 | KCL-105 |
| 4.7 | With Prometheus scaled to 0 the cards still show and the trend says unavailable; scale back to 1 | Kubernetes API `deployments/scale` in `table-metrics` to 0; `GET /v1/tables/{uuid}/metrics/current` -> 200 with counts, `GET .../metrics?range=1h` -> 502 with a reason; scale to 1 and poll until the trend answers 200. Cleanup scales to 1 first; the sweep also does | `MetricHistoryUnavailableError` -> 502 (unit-tested). Costs ~1-2 min of lost scrapes; needs Role in `table-metrics`: `apps` `deployments/scale` `get,update,patch`. Lowest value; optional | AUTO-full | `test_metric_trends.py` (last test; skip if the Role is not wanted) |
| 4.8 | `gates:pre-pr` and record results | -- | gate | MANUAL [superseded] | none |

## Source 5. `2026-11-20-schema-version-diff.md`, Task 10 (KCL-97)

All run on one owned table in an own catalog (or a namespace of `iceberg`), managed by a dry-run policy so `/commits` works.

| # | check (plain words) | how to verify (API calls, expected answers) | code today | class | scenario group suggestion |
|---|---|---|---|---|---|
| 5.1 | Rebuild and `apps:validate` | -- | deployment validation | MANUAL [infra] | none |
| 5.2 | Create a table with nested and partition columns, evolve it, append once after each stage | Setup: `POST /v1/catalogs/{c}/namespaces/{ns}/tables` (`order_id int`, `customer_id long optional`, `order_ts timestamptz optional`, `shipping struct<city: string> optional`, partition `day(order_ts)`) or PyIceberg; evolve with PyIceberg: rename, widen + make optional, add `shipping.zip` in one commit, then change the spec to `hour(order_ts)`; append a row after each stage (the plan ran this in the API pod; e2e has PyIceberg) | schemas, specs and snapshot `schema_id` kept per table | AUTO-critical | `test_table_information.py` (setup) |
| 5.3 | `schema-versions` lists versions newest first with change counts | `GET /v1/catalogs/{c}/namespaces/{ns}/tables/{t}/schema-versions`: `current_schema_id 1`, ids `[1, 0]`, v1 `previous_schema_id 0`, `current true`, `changes {added 1, removed 0, renamed 1, type_changed 1, nullability_changed 1, doc_changed 0}`, v0 `changes null` | `list_table_schema_versions` | AUTO-critical | `test_table_information.py` |
| 5.4 | The schema comparison matches fields by id and shows each change; unknown base is 404 | `.../schema-versions/1/comparison`: renamed column `changes ["renamed"]`, `previous_path ["customer_id"]`, `path ["customer"]`; `order_id` `["type_changed","nullability_changed"]`; `["shipping","zip"]` `["added"]`, `depth 1`; untouched `[]`; `?base=9` -> 404; version 0 has `base_schema_id null` | `get_table_schema_comparison` | AUTO-critical | `test_table_information.py` |
| 5.5 | Partition spec versions and their comparison | `.../partition-spec-versions`: `default_spec_id 1`, `[1, 0]`; v1 changes `transform_changed 1`; `.../partition-spec-versions/1/comparison`: one row `["transform_changed"]`, `previous_transform "day"` -> `"hour"`, expressions `day(order_ts)` -> `hour(order_ts)` | `compare_partition_specs` pairs removed+added on one source column; a rename counts only when names are not Iceberg's defaults | AUTO-critical | `test_table_information.py` |
| 5.6 | Each commit carries the schema version it was written with | `GET /v1/tables/{uuid}/commits` (uuid from `GET /v1/tables` once managed): three items, `schema_id` `[1, 1, 0]` newest first; `truncated false` | `TableCommitApiResponse.schema_id`. Newest-first order vs PyIceberg is covered by `test_manual_maintenance.py`; `schema_id` is new | AUTO-critical | `test_table_information.py` |
| 5.7 | Console: Schema tab version lists and comparison, "Show changes only", "Compare with", partition panel, DDL note, Commits tab links, 390 px, delete the demo table | -- | visual and interaction | MANUAL [visual] | story tests |
| 5.8 | Record results, gate | -- | gate | MANUAL [superseded] | none |

## Source 6. `2026-11-11-maintenance-policy-and-discovery-rules.md`, Task 14

| # | check (plain words) | how to verify (API calls, expected answers) | code today | class | scenario group suggestion |
|---|---|---|---|---|---|
| 6.1 | Build/deploy, offboard/onboard, `apps:validate`, `e2e.sh` | -- | deployment steps; `e2e.sh` retired | MANUAL [superseded] | none |
| 6.2 | Saving a rule list that excludes a managed table unmanages it and its workflow ends | Re-expressed for discovery policies (the discovery-rules API is gone): managed table in an own catalog; `PUT /v1/discovery-policies/{p}` with rules that no longer match (version +1); poll (<= 60 s): table `unmanaged`, reconciliation workflow got `stop` and is not running; restore the matching rule: managed again | update rescans every catalog the policy is attached in | AUTO-critical | `test_discovery_lifecycle.py` |
| 6.3 | Attaching a policy to a namespace makes the tables' next reconciliation name it | same as 3.6 | see 3.6 | AUTO-critical (duplicate of 3.6) | `test_policy_records.py` |
| 6.4 | Opening an old policy version from a reconciliation row works | after the policy goes to version 2, `GET /v1/maintenance-policies/{name}/versions/1` -> 200 with the original content; `.../versions/99` -> 404. The click-through is not covered | `get_table_maintenance_policy_version` | AUTO-critical | `test_policy_records.py` |
| 6.5 | Add the project-history line, commit | -- | not a verification | MANUAL [superseded] | none |

## Source 7. Other plans in `docs/superpowers/plans/` with cluster checks of the same kind

| # | plan file / step | check (plain words) | how to verify (API calls, expected answers) | code today | class | scenario group suggestion |
|---|---|---|---|---|---|---|
| 7.1 | `2026-11-20-discovery-policy.md` Task 16 step 4 (older draft of KCL-71, superseded) | The discovery schedule fires at the platform's discovery interval | own catalog with an attachment: `describe()` of `table-discovery:catalog=<c>` interval equals `GET /v1/platform-settings` `discovery_interval_seconds` (600 default, not "5m"). The plan's variant (change the Helm value, restart the worker) is MANUAL [deploy-change]: it changes the shared release | `build_gateways.py` passes `discovery_interval_seconds` | AUTO-critical (read-only equality) | `test_discovery_lifecycle.py` (extra assert) |
| 7.2 | same file, other steps (rebuild, attach, nearest wins, console, `e2e.sh`) | same as Source 1 | -- | superseded by the 2026-11-21 plan | MANUAL [superseded] | none |
| 7.3 | `2026-11-23-code-quality-batch-1.md` Task 12 step 3 | Attach a managing policy, create a partitioned table, see it managed | = 1.2 | covered by 1.2 | AUTO-critical (duplicate) | `test_discovery_lifecycle.py` |
| 7.4 | same | The reconciliation record carries its typed policy target (type + path) | `GET /v1/tables/{uuid}/reconciliations`: `policy_target == {type, path}` for the level the policy came from, `null` for the default | `ReconciliationPolicyTargetApiResponse` | AUTO-critical | `test_policy_records.py` (assert inside 3.6) |
| 7.5 | same, and `2026-11-24-state-change-guard-gaps.md` Task 4 step 3 | `GET /v1/tables/{uuid}` reads every operation state | 200; `operation_states` has the four operations for a managed table, `matched_*` set, `priority` `P3` by default | `TableApiResponse.operation_states` | AUTO-critical | `test_table_information.py` |
| 7.6 | `2026-11-24-state-change-guard-gaps.md` Task 4 step 3 | Catalog context namespace and table GET answer 200 with `properties` and snapshots | namespace `properties`; table `properties`, `snapshots`, `current_snapshot_id`, `uuid` equal to PyIceberg's | catalog `router.py` GET routes. Mostly covered by `test_catalog_round_trip.py` and `test_manual_maintenance.py` | AUTO-critical (mostly already covered) | add the table-GET `properties` assert to `test_table_information.py` |
| 7.7 | `2026-11-23-code-quality-batch-1.md` Task 12, `2026-11-24-state-change-guard-gaps.md` Task 4 | api/worker/event-consumer logs contain no `nondeterminism`, `TypeError`, `ValidationError`, `KeyError`, `Traceback` since the redeploy | -- | reads pod logs over a deploy window and judges noise; needs `pods/log` RBAC | MANUAL [logs] | none |
| 7.8 | `2026-11-24-state-change-guard-gaps.md` Task 4 step 2 | Redeploy the backend (`bootstrap.sh`, `validate.sh`) | -- | deployment | MANUAL [infra] | none |
| 7.9 | `2026-11-19-prefixed-resource-ids.md` Task 9 step 2 | Run, reconciliation, rule and policy ids carry prefixes | `assert_prefixed_ids` in `test_manual_maintenance.py`; new scenarios assert the ids they create (`dp`, `da`, `dr`, `mp`, `pa`) with the same helper | existing | AUTO-critical (already covered by `test_manual_maintenance.py`) | existing |
| 7.10 | same, "Spark application names use the run suffix" | -- | needs `kubectl get sparkapplications`; belongs with KCL-105 | MANUAL [infra] | none |
| 7.11 | `2026-11-10-pydantic-domain-model.md` step 4 | Table settings page loads and saving settings round-trips | the settings page and per-table settings no longer exist (policies replaced them); reconcile-now is in `test_manual_maintenance.py` | gone | MANUAL [superseded] | none |
| 7.12 | `2026-11-07-backend-bounded-contexts.md` Task 6, `2026-11-18-architecture-conformance-round-1.md` Task 13, `2026-11-07-backend-ruff-and-frontend-move.md` Task 5, deploy plans | build, deploy, `validate.sh`, `e2e.sh`, pods Running | -- | deployment/infra validation | MANUAL [infra] | `validate.sh`, `deployment-test` gate |
| 7.13 | `2026-11-07-catalog-context.md` | no cluster-verification section | -- | `test_catalog_round_trip.py` is its e2e | none | already covered by `test_catalog_round_trip.py` |

## Source 8. Belongs to KCL-105 (by title only)

* `2026-11-21-one-operation-per-run.md` Task 12 (KCL-95): manual run of four operations in order; scheduled plan with two operations due; raise to P0; skip on cancel; callback path; Temporal summary; console side panels; e2e. (Four manual runs already in `test_manual_maintenance.py`.)
* `2026-11-20-partition-selected-compaction.md` Task 10 (KCL-94): partition-selection settings, cap and order, quiet period and max wait, transforms and spec evolution (needs a chart change), manual run `filters: []`, console.
* `2026-11-20-per-table-maintenance-workflow.md` Task 14 (KCL-93): several tables due queue by priority, one table never runs two maintenances, P0 resubmits a waiting P3 run, queue wait does not trip the timeout, `compaction-rounds` gone (404 route check is 2.8).
* `2026-11-19-table-priority-volcano-queues.md` Task 9 (KCL-92): PodGroup queue, class and size; P3/P0 admission; priority P1 -> its PodGroup. (The API half, `PUT /v1/tables/{uuid}/priority` returning `priority "P1"` and `GET /v1/tables` agreeing, is a 2-second API check KCL-105 can take.)
* `2026-11-13-milestone-1-timeout-fencing.md`, `-2-failure-classes-and-oom.md`, `-3-partition-candidates.md`, `-4-priorities-and-budget.md` "Verification on the cluster": timeouts, OOM sizes, candidate top-N, budget rounds.
* `2026-11-10-reconciliation-records.md` Tasks 12-13: records by schedule / reconcile-now / catalog commit, dry-run "would start", terminate-and-restart of reconciliation workflows, drawer at phone width. (Reconcile-now record is in `test_manual_maintenance.py`.)
* Timing halves of this inventory: 3.7 (debounce and schedule gap), 3.8 (600 s gap), 3.9 (expiry run), 4.6 (compaction lowering the cards).

---

## Proposed scenario modules

New files in `src/data-platform/backend/e2e/`. Shared pieces to add first: a per-catalog PyIceberg fixture, `ManagedTable` taking a catalog, an own-catalog helper (create via `POST /v1/catalogs`, grant revoke/restore, cleanup order), "re-grant before drop" in `sweep_leftovers`, and Temporal helpers (schedule describe/list, workflow history `stop` signal).

| module | marker | est. time | checks |
|---|---|---|---|
| `test_discovery_policies.py` | critical | ~20-30 s | 1.1, 1.5, 1.6, 1.12 |
| `test_discovery_lifecycle.py` | critical | ~1.5-2.5 min | 1.2, 1.3, 1.4, 6.2, 7.1, 7.3 |
| `test_discovery_unreadable_catalog.py` | critical | ~1-2 min | 1.7, 1.8, 2.5 (403 half); needs grant revoke/restore |
| `test_worker_restart_schedules.py` | full | ~3-5 min | 1.10; needs e2e ServiceAccount + Role (`pods` get/list/watch/delete or `deployments` get/patch in `lakehouse-control-plane`) and `pod.yaml` changes |
| `test_effective_policies.py` | critical | ~20-40 s | 2.1, 2.2, 2.3, 2.5 (404 half), 2.7 |
| `test_removed_routes.py` | critical | ~2 s | 2.4, 2.8 |
| `test_maintenance_policies.py` | critical | ~10 s | 3.2, 3.3, 3.4 |
| `test_policy_records.py` | critical | ~1.5-2 min | 3.5, 3.6, 3.8, 3.9, 6.3, 6.4, 7.4 (one dry-run managed table, module-scoped) |
| `test_table_information.py` | critical | ~1-2 min | 4.2, 5.2-5.6, 7.5, 7.6 (one owned managed table, evolved once) |
| `test_metric_trends.py` | full | ~3-5 min | 4.4 (no extra RBAC), 4.7 (needs Role in `table-metrics`; optional) |

Totals: the critical modules add about 6-9 min if run serially (the existing critical suite is ~1 min). If that is too long for pre-merge, `test_policy_records.py` and `test_table_information.py` can share one managed table and drop to ~3 min together, or move to `full`. Full modules add ~6-10 min (nightly).

Isolation: each module owns its catalog/namespace/policy names from `OwnedNames`; the sweep must learn any new name pattern (policy names matching `tm-e2e-<scenario>-<suffix>`).

## Full MANUAL list (with reasons)

| # | check | reason |
|---|---|---|
| 1.9 | console banner and "cannot read this catalog" message | visual copy and placement; stories exist |
| 1.11 | console flows of the discovery policy pages (1280 px and 390 px) | layout, redirects, keyboard and responsive behaviour; the API half is 1.12 |
| 1.13, 3.11, 4.8, 5.8, 6.5, 7.2 | `e2e.sh` pass, `gates:pre-pr`, project-history line, old-draft steps | `e2e.sh` retired by KCL-102; gates and history lines are not cluster behaviour; old draft superseded |
| 1.14 | empty `scanned-catalogs` / no schedule on a fresh cluster | rebuild state, not assertable on a shared long-lived platform; `apps:validate` owns it |
| 2.6 | effective-policies console panel | visual; stories |
| 3.1, 4.1, 5.1, 6.1, 7.8, 7.12 | rebuild, deploy, `apps:validate`, `validate.sh`, pods Running | infrastructure validation owned by deploy tasks and gates |
| 3.10 | policy editor keyboard use, "Checks" text, "Not in this policy", settings page | visual and keyboard judged by a person |
| 4.3 | MySQL inserts through Debezium and the Iceberg sink | needs MySQL/Kafka/sink outside the e2e surfaces and takes up to 10 min; its table effect is 4.4 |
| 4.5 | Overview cards, sections, range switching | visual |
| 5.7 | Schema and Commits tabs, phone width | visual and interaction |
| 7.7 | logs free of `nondeterminism`/`TypeError`/`KeyError`/`Traceback` | reads pod logs over a deploy window and judges noise |
| 7.10 | Spark application names carry the run suffix | needs `kubectl get sparkapplications`; with KCL-105 |
| 7.11 | table settings page and saving settings | feature no longer exists |
| 7.1 (variant) | change `worker.discoveryIntervalSeconds` with `helm upgrade`, restart, wait | changes the release of the shared platform; the read-only equality is automated |

## Counts

Rows per class, from the tables above (duplicates and already-covered rows are counted in the main class and noted):

* AUTO-critical: 38 rows (1.1-1.8, 1.12 = 9; 2.1-2.5, 2.7, 2.8 = 7; 3.2-3.6, 3.8, 3.9 = 7; 4.2 = 1; 5.2-5.6 = 5; 6.2-6.4 = 3; 7.1, 7.3-7.6, 7.9 = 6). Of these 6.3 and 7.3 duplicate other rows and 7.9 is already covered, and 7.6 is mostly covered, so about 34 are distinct new checks. 1.8 becomes AUTO-full if the rescan does not record the failure.
* AUTO-full: 3 rows (1.10, 4.4, 4.7).
* MANUAL: 23 rows (visual 6: 1.9, 1.11, 2.6, 3.10, 4.5, 5.7; infra 7: 1.14, 3.1, 4.1, 5.1, 7.8, 7.10, 7.12; superseded 8: 1.13, 3.11, 4.8, 5.8, 6.1, 6.5, 7.2, 7.11; cdc 1: 4.3; logs 1: 7.7). The 7.1 deploy-change variant is a sub-variant of an automated row and not counted.
* KCL-105 (not counted): 3.7, 4.6 in the tables plus the titles in Source 8.
