# Discovery Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Written 2026-11-21 against HEAD `c08d372d`** (KCL-95's last docs commit). A small KCL-95 fix wave may land after it. Every file this plan names was read at that HEAD; read it again at the HEAD you start from before changing it. This plan replaces `docs/superpowers/plans/2026-11-20-discovery-policy.md`, which was written before KCL-93 to KCL-97 landed; do not follow that one.

**Goal:** The one platform-wide discovery rule list becomes named, versioned discovery policies. A policy is attached to catalogs, namespaces and tables, and the attachment nearest a table decides whether maintenance manages it. The catalogs that are scanned follow from the attachments, so their schedules are created and deleted to match. A catalog the platform cannot read shows as "cannot access". The console has a policy list, an edit page and a read-only version page that shows what each version changed.

**Architecture:**
- Two new aggregates in `table_maintenance` replace `TableDiscoveryRules`:
  - `TableDiscoveryPolicy`: a `dp-` id, a name, kept versions, and content made of ordered rules plus a no-match outcome;
  - `TableDiscoveryPolicyAttachment`: a `da-` id, one per target.
- `PolicyTarget` and the walk up the catalog hierarchy move to the context's `shared` model, with one `nearest_attached` pick. Maintenance and discovery resolve the same way (ADR 0012).
- Every scan resolves each table's nearest discovery attachment. The table records which policy, version and rule decided it.
- Every change to a policy or an attachment works out the scanned catalogs again. It then:
  - syncs one Temporal schedule per scanned catalog;
  - rescans the catalogs it affects.
- A scan that the catalog refuses is recorded on `CatalogDiscovery`. `GET /v1/scanned-catalogs` reports each scanned catalog with its last scan and its failure.
- Removed: `TableDiscoveryRules`, `/v1/discovery-rules*` and `GLAC_CATALOG__NAMES`.

**Tech Stack:** Python 3.14, Pydantic, SQLAlchemy Core, FastAPI, Temporal Python SDK (schedules), PyIceberg 0.11, Helm, React + TanStack Query + orval + MSW, Storybook/vitest.

**Spec:**
- Linear KCL-71, copied at `/Users/kcl/.claude/jobs/ffac9ee8/tmp/kcl71/spec.md`. The 2026-11-19 scope change is binding and overrides the description where they conflict.
- ADR 0012 (`docs/adr/0012-policies-on-the-catalog-hierarchy.md`, "Discovery policy" and "Aggregates and API") is the model. ADRs 0005, 0006, 0009, 0010 and 0011 apply.
- KCL-98, the next issue, owns these, and no task here touches them:
  - `effective-policies`;
  - the per-target policy panel;
  - the maintenance `mappings` → `attachments` change;
  - the removal of `applicable-policy`.
- **Read each file at HEAD before changing it; never apply a step against a remembered version.**

`<pytest>` is `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend pytest`. `<vitest>` is `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend test -- --run`. `<stories>` is `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run test:stories --`. `<gate> X` is `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=X`. `<generate>` is `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`.

## Global Constraints

Decisions this plan makes are marked **(decided)** with the reason. Everything else comes from the spec's binding scope or ADR 0012 and is not reopened.

### The policy

- **The platform default** is id `dp-00000000000000000000000000`, named `default`. It has no rules and its no-match outcome is `unmanage`. Its description is `Manages nothing. Attach another discovery policy to a catalog, namespace or table to manage its tables.` An update or a delete of it is 409.
  - **(decided)** It may be attached anywhere. Attaching it to a namespace or a table under a managing catalog is how a user opts that part out, which "the nearest replaces its parents whole" already implies.
  - **(decided)** It is seeded by `migrate`, like the maintenance default, so it has a row to attach and a version page. A scan never reads it: "nothing attached" decides with its fixed content at version 1, the only version it can have.
- **Content wire shape (decided).** It is modelled on Kubernetes `matchExpressions` (`{key, operator, values}`), so labels and table properties later add an attribute or an operator, not a new structure. It is ADR 0012's "a condition names the attribute it reads and how it matches":

  ```json
  {"description": "", "no_match_outcome": "unmanage",
   "rules": [{"id": "dr-…", "outcome": "manage",
              "conditions": [{"attribute": "namespace", "operator": "glob", "values": ["sales", "sales.*"]},
                             {"attribute": "table_name", "operator": "glob", "values": ["orders_*"]}]}]}
  ```

  - Outcomes are `manage` and `unmanage` **(decided: the words of `Table.manage()` / `unmanage()` and of the statuses)**. The console says "Manage" and "Do not manage".
  - Attributes are `namespace` and `table_name` **(decided: `table_name` names what it reads, and a later `property` attribute would make a bare `table` ambiguous)**. The only operator is `glob`.
- **Rules (ADR 0012).** They are read top to bottom, and the first rule whose conditions all hold decides. When none does, `no_match_outcome` decides. A rule has at least one condition.
  - **(decided)** An attribute appears at most once per rule, since two `namespace` conditions that must both hold are a confusing way to write one. `values` is non-empty and holds no empty string.
  - Globs keep today's semantics: `fnmatchcase`, case-sensitive. A namespace glob matches the dot-joined namespace, and `*` crosses dots.
  - **(decided)** Rules have no `priority` and no `enabled`. The list order is the order ("ordered rules"), and the kept versions make removing a rule safe where `enabled` used to be the undo.
- **Rules are value objects with a `dr-` id (decided).** A version never changes, so its rules are values. The id is what links a table to its rule across versions and edits.
  - The server mints an id for every rule sent without one. An update may name only ids of the policy's current version, and any other id is 422 `unknown discovery rule id dr-…`. A create may name none.
  - `"id": ""` is 422 `a rule id is a dr- id or absent`. This closes the KCL-73 follow-up about an empty id.
- **Names.** A name is 1 to 64 of `[A-Za-z0-9_-]` and never shaped like a prefixed id. Names are unique per kind, so a discovery and a maintenance policy may share one (ADR 0012).
  - **(decided)** One shared checker, `checked_policy_name`, serves both name value objects. This closes the KCL-73 follow-up that `TableMaintenancePolicyName` copies the id pattern by hand: the checker uses `shared_kernel.prefixed_id_pattern`.
- **"Could resolve to manage" is syntactic (ADR 0012).** `can_manage()` holds when the policy has a `manage` rule or `no_match_outcome` is `manage`.
  - **(decided)** A `manage` rule that an earlier catch-all `unmanage` hides still counts. The check stays cheap and errs towards scanning; a wasted scan manages nothing.

### Attachments and resolution

- **`PolicyTarget` moves to `shared` now, in KCL-71 (decided).**
  - What moves to `TM/application/domain/{model,service}/shared/`: `PolicyTarget`, `PolicyTargetType`, `candidate_policy_targets` and `enclosing_policy_targets`. A new `nearest_attached` joins them, and maintenance's two resolvers (`notify_policy_change`, `ResolveApplicableTableMaintenancePolicyService`) call it.
  - Why: the discovery attachment cannot be built in ADR 0012's shape without a target type. A copy would leave KCL-98 two `PolicyTarget`s to merge, and the move changes no behaviour or route.
  - KCL-98 keeps the rest of its list: the maintenance API rename, `effective-policies`, the panel, and removing `applicable-policy`.
- **Attachment ids are `da-` (decided: "discovery attachment").** `pa-` stays the maintenance attachment's, and ADR 0011's list gets the row. A target holds one discovery attachment: `PolicyTarget.key()` is a unique index.
  - **(decided)** The row also stores the target's catalog in an indexed `catalog` column, so a scan reads only its catalog's attachments. An Iceberg table cannot leave its catalog, so a table attachment's catalog never goes stale.
- **Resolution (ADR 0012).** A table walks, nearest first, until the first attachment, which replaces its parents whole:
  1. its own attachment (by Iceberg uuid);
  2. its namespaces, deepest first;
  3. its catalog;
  4. the default.
  - An attachment whose policy is gone is skipped, which can only happen in a race with a delete.
- **A target must exist when it is attached (decided: the first place a discovery policy goes is often an empty catalog, which today's check refuses).**
  - A catalog or namespace may be empty. `ReadTableMetadataGateway` gains `catalog_exists` and `namespace_exists` (PyIceberg `namespace_exists`), replacing "holds a table".
  - The same shared helper serves maintenance attachments, so maintenance may now attach to an empty catalog too. That only adds what was refused.
  - A table is still resolved to its uuid through the catalog. A target that does not exist is 404.
- **A catalog the platform's credential may not read is 403 (decided).** The detail is `the platform's catalog credential cannot read catalog <name>`. The table-reading gateway raises the new `CatalogAccessDeniedError` for PyIceberg's `ForbiddenError` and `UnauthorizedError`.
- **Detach is by attachment id (decided).**
  - `DELETE /v1/discovery-policies/{name}/attachments/{attachment_id}`, so the responses carry `id`.
  - Why: a request body on DELETE has no defined semantics (RFC 9110 §9.3.5), and today's maintenance route depends on one. Detaching by id also works for an orphaned target, with no catalog lookup.
  - Attach stays `PUT …/attachments` with `{"target": {"type", "path"}}`, as maintenance's attach is today. It is idempotent and replaces whatever the target held, keeping that attachment's id.
  - KCL-98 copies this shape for maintenance. ADR 0012 gets a dated note saying so.

### Scanning and schedules

- **Scanned catalogs are derived.** A catalog is scanned when a discovery attachment in it (a catalog, namespace or table target) points at a policy that `can_manage()`.
  - Each scanned catalog has the Temporal schedule `table-discovery:catalog={catalog}` (id unchanged), firing every `GLAC_DISCOVERY_INTERVAL_SECONDS`. No other `table-discovery:catalog=` schedule exists.
  - The interval stays a platform setting, unchanged.
- **After a change (decided).** An update, an attach and a detach each run the same steps after the change commits:
  1. Work out the scanned catalogs before and after the change.
  2. Sync the schedules to the "after" set: create the missing ones, rewrite the interval of existing ones and unpause them, delete the extra ones.
  3. Start one ad hoc catalog-wide scan for every affected catalog that is scanned before or after. An update affects every catalog the policy is attached in; an attach or a detach affects the target's catalog.
  - **What happens to managed tables in a catalog that stops being scanned (decided): they become unmanaged.** The catalog gets one last scan, in which each table resolves under the new attachments and is unmanaged and sent `stopped`, as an `unmanage` decision does today. Then it has no schedule. Tables that stay managed under no scan would be maintained by a policy that no longer applies.
  - Steps 2 and 3 are best effort, as starting discovery after a rules save is today. A failure is logged and never fails the request.
  - Create and delete do neither: an unattached policy affects no table, and a delete is refused while attached.
- **Schedules on worker start versus on save (decided).** The worker syncs the schedules at every start, after the search-attribute check, and a failure there stops the start, loudly.
  - A save syncs best effort, as above.
  - Two saves at the same moment can sync in the wrong order, the later sync deleting a schedule the other needed. That lasts until the next change or worker start, and it is listed as a follow-up. A separate reconcile schedule would close it.
- **Each change gets its own scan.** `SendDiscoveryRequestGatewayInput.rules_version` becomes `change_id: str | None`. A change's scan has the workflow id `table-discovery:catalog={catalog}:trigger=policy-changed:change={change_id}`, with a fresh 32-hex `uuid4` per change.
  - This keeps today's guarantee that a save never joins a run that read older settings, now that there is no single rules version.
- **"Cannot access" is recorded, not thrown (decided).** A catalog-wide or namespace scan whose catalog refuses the credential (`CatalogAccessDeniedError`), or no longer exists (`CatalogNotFoundError`), records a `CatalogScanFailure` on the catalog's `CatalogDiscovery`. The scan changes no table and returns normally with `failure` set.
  - Why: retrying a refusal five times changes nothing, and the record is what the console reads.
  - Any other error still fails the activity and retries, as today.
  - A catalog's failure is current only while it is newer than the catalog's last completed scan. Both writes are forward-only and independent, so a later good scan clears the failure without deleting it.
  - **(decided)** A single table the credential cannot load is counted in `skipped`, and that scan drops no table. A table that cannot be read must never read as dropped.
- **A catalog event for a refused catalog is dropped** (logged), as an unknown catalog is today. The next scan records the failure.

### Tables

- **The table records the decision (decided).** `Table` gains `discovered_by: DiscoveryMatch`, which holds the policy id, its version, and the deciding rule id or `None`. `matched_rule_id` becomes a property that reads `discovered_by.rule_id`, and its column and API field stay, so it "still points at a rule".
  - Why: a rule id alone does not say which policy or version holds it. The Overview names "the policy and version that decided", as reconciliation records name the maintenance policy by id and version (`AppliedPolicyRef`).
  - A table managed by the no-match outcome has `rule_id = None`.
  - Every table has one: a table is only ever registered by a discovery decision.
- `TableManagementChange.RULE_CHANGED` becomes `MATCH_CHANGED`. It means management did not change but the deciding policy, version or rule did. The row is saved and nothing is sent.
- **No migration (spec).** Old rules are not converted and the cluster is rebuilt. Code stops creating `table_discovery_rules` and `table_discovery_rule_items`; it never drops them.

### API

All routes carry the tag `discovery-policies`, so orval puts them in one client module. Request DTOs are `extra="forbid"`.

| Route | Answer |
|---|---|
| `GET /v1/discovery-policies` | `{policies: [...]}`, each with `attachment_count`, the default first then by name |
| `POST /v1/discovery-policies` | 201; body `{name, description = "", no_match_outcome, rules}` |
| `GET`, `PUT`, `DELETE /v1/discovery-policies/{name}` | `PUT` body `{version, description, no_match_outcome, rules}`; `DELETE` 204 |
| `GET /v1/discovery-policies/{name}/versions/{version}` | one kept version |
| `GET /v1/discovery-policies/{name}/attachments` | `{attachments: [{id, target, policy_id, policy_name, attached_at, orphaned}]}` |
| `PUT /v1/discovery-policies/{name}/attachments` | 200 `{id, target, policy_id, policy_name, attached_at}`; body `{target: {type, path}}` |
| `DELETE /v1/discovery-policies/{name}/attachments/{attachment_id}` | 204 |
| `GET /v1/scanned-catalogs` | `{catalogs: [{catalog, last_discovered_at, failure: {reason, detail, failed_at} \| null}]}` sorted by name |

- `/v1/scanned-catalogs` is top level so it never collides with a policy named `scanned-catalogs` **(decided)**. It replaces `GET /v1/discovery-rules/catalogs`. `reason` is `cannot_access` or `not_found`.
- Errors:
  - 404: an unknown policy, target or attachment, or an attachment of another policy;
  - 409: a taken name, a stale version, a change to the default or its delete, a delete while attached;
  - 422: invalid content, an unknown or empty rule id, a malformed `da-` id;
  - 403: a catalog the credential cannot read.
- `TableApiResponse` keeps `matched_rule_id` and gains `matched_policy_id: str` and `matched_policy_version: int`.

### The console

- **Routes (decided).**
  - `/discovery-policies` is the list.
  - `/discovery-policies/:name` is the edit page. The rules are a page-level draft with Save and Discard, as the rules page is today; that is too much for a dialog.
  - `/discovery-policies/:name/versions/:version` is read-only.
  - `/discovery-rules` redirects to `/discovery-policies`, for bookmarks.
  - The sidebar entry reads "Discovery policies".
- **Attach and detach live on the policy's edit page (decided)** until KCL-98 puts them on the target pages.
  - The catalog is picked from `GET /v1/catalogs` (the spec's "pick from Polaris's catalogs").
  - The namespace (dot-joined) and the table are typed: they can be many and nested. A missing one is the API's 404, shown in the dialog.
- **The "condition without effect" hint is computed in the console (decided: ADR 0012 says the console hints, and the API accepts every condition).** There are two hints:
  - a policy attached to a table: "On a table, a rule either always or never matches it.";
  - a policy attached to a namespace, on a rule with a namespace glob: "Attached to namespace `<path>`: a namespace glob only tells its child namespaces apart."
- **What each version changed is computed in the console (decided: the user story is "look back at what each version changed"; the content is a short list, and rule ids make the comparison exact, so it needs no route).** The version page reads `vN` and `vN-1` and lists:
  - the rules added, removed, changed or moved, by id;
  - the no-match outcome, when it changed;
  - the description, when it changed.
- **"Cannot access" shows in three places (decided).**
  - The list page shows a negative `Banner` per failing scanned catalog.
  - Each attachment row shows its catalog's scan state.
  - The table page shows a new empty-state reason, `catalog-cannot-access`.
  - The catalog's state comes from `GET /v1/scanned-catalogs`.
- **Table page (decided).**
  - `tableMaintenanceState` reads `useListScannedCatalogs`, and "catalog not covered" becomes `catalog-not-scanned`.
  - The Overview's Table panel replaces "rule Priority N" with "discovery policy `<name>` v`<N>`", linking to the version page, then "· rule `<position>`" or "· no rule matched".
  - The name comes from `useListTableDiscoveryPolicies` by `matched_policy_id`, and the position from that version. A policy deleted since shows its id in mono.

### Commits and gates

- **No red stretch.** Every task commits on its own and passes `<gate>` for the side it changes (`all` when both change).
- **An API change commits with its regenerated `openapi.json` and client, and with every console file `tsc` needs** (`contract-test` and `tsc` gate every commit).
  - Task 7 adds two required fields to `TableApiResponse`, so it updates the console fixtures in the same commit.
  - Task 14 deletes the `discovery-rules` client module, which Task 13 has already stopped importing.
- Between Task 7 and Task 14 the old rules API still answers, but no scan reads it. That is acceptable for the commits between, never for a deploy.
- Commit messages end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`. `git add` names explicit paths, and no hook is skipped.

## Review Focus

- **The nearest wins over a managing parent (Tasks 3 and 7).** A table carrying `default` on itself, under a catalog whose policy manages `*`, stays unmanaged. A table attached by uuid keeps its own policy after a rename to another namespace, and the namespace part of its walk then uses the new name.
- **Leaving the scanned set (Task 9).** Detaching the last managing policy in a catalog has three effects: one final scan unmanages the catalog's managed tables (each is sent `stopped`), and the schedule is deleted. A Temporal failure while doing so still answers 204 and logs.
- **Refused and missing catalogs (Tasks 6 and 8).** Attaching to an empty catalog or namespace succeeds, a missing one is 404, and an unreadable one is 403 with nothing stored. A scan of an unreadable catalog records `cannot_access`, changes no table and is not retried, and the next good scan makes the failure no longer current. A table refused mid-scan is not dropped.
- **Refused updates leave no trace (Tasks 5 and 9).** An update that names another policy's rule id, an empty id or a stale version saves nothing, syncs no schedule and starts no scan.
- **A catalog event in an unscanned catalog (Task 7)** registers the table as unmanaged, decided by the default, and sends no table change. It never fails the hint.

---

## File Structure

Paths and abbreviations:
- Backend paths are relative to `src/data-platform/backend/`. `TM` = `context/table_maintenance`, and tests mirror under `tests/context/table_maintenance/`.
- `DP` = `TM/application/domain/model/table_discovery_policy`; `DA` = `TM/application/domain/model/table_discovery_policy_attachment`.
- `FE` = `src/data-platform/frontend/src`.

| File | Responsibility |
|---|---|
| `TM/application/domain/model/shared/{policy_target,policy_target_type,checked_policy_name}.py`, `TM/application/domain/service/shared/{candidate_policy_targets,enclosing_policy_targets,nearest_attached}.py` | the target and the walk up the hierarchy (moved), the nearest pick, the name rule |
| `TM/application/service/shared/{policy_target_from_request,target_in_catalog}.py`, `TM/adapter/inbound/web/shared/dto.py` | request → target, existence and orphan checks, the target DTOs (moved) |
| `DP/*` (new) | the policy aggregate, its content, rules, conditions, decision, ids, name and errors |
| `DA/*`, `TM/application/domain/service/table_discovery_policy_attachment/{decide_table_discovery,scanned_catalogs}.py` (new) | the attachment aggregate and resolution |
| `TM/application/port/{inbound,outbound}/table_discovery_policy{,_attachment}/` (new) | use cases, repos, `SyncDiscoverySchedulesGateway` |
| `TM/application/service/table_discovery_policy{,_attachment}/` (new) | services, `apply_discovery_change` |
| `TM/adapter/outbound/table_discovery_policy{,_attachment}/sql/` (new) | SQL tables, mappers, repos |
| `TM/adapter/inbound/web/table_discovery_policy{,_attachment}/`, `TM/adapter/inbound/web/catalog_discovery/` (new) | routers, DTOs |
| `TM/adapter/hybrid/temporal/outbound/table_discovery_policy_attachment/` (new) | the schedule sync gateway and the schedule body |
| `TM/application/domain/model/{table/table.py,catalog_discovery/*}`, `TM/application/service/table/{discovery_decider (new),sync_discovered_tables,register_discovered_table,apply_discovery_to_known_table,process_table_hint}.py`, `TM/application/domain/service/table/decide_table_management.py` | scans decide by policy and record refusals |
| `TM/application/port/outbound/table/read_table_metadata/{gateway,catalog_access_denied_error (new)}.py`, `TM/adapter/outbound/table/pyiceberg/read_table_metadata_pyiceberg_gateway.py` | existence checks, refused catalogs |
| `bootstrap/{configs,container}/*`, `bootstrap/worker.py` | wiring, the startup sync, the settings |
| removed: `TM/**/table_discovery_rules/`, `TM/adapter/hybrid/temporal/inbound/ensure_table_discovery_schedule.py`, `ListCoveredCatalogs*` | the old aggregate |
| `FE/pages/{DiscoveryPoliciesPage,DiscoveryPolicyPage,DiscoveryPolicyVersionPage}.tsx` (new) | console pages |
| `FE/components/{CreateDiscoveryPolicyDialog,DiscoveryRulesTable,DiscoveryRuleEditor,DiscoveryPolicyAttachments,AttachDiscoveryPolicyDialog}.tsx` | console components |
| `FE/lib/{discoveryPolicyDraft,discoveryPolicyPaths,discoveryRuleHints,discoveryPolicyChanges}.ts` | console logic |
| `platform/25-lakehouse-control-plane/{chart/values.yaml,chart/templates/configmap.yaml,validate.sh,e2e.sh,README.md}` | platform |

---

### Task 1: Move the policy target and its walk to `shared`

A refactor plus one behaviour change for maintenance, the existence check of Global Constraints, kept in its own step. Routes and `openapi.json` stay byte for byte the same.

**Files:**
- Move:
  - `TM/application/domain/model/table_maintenance_policy_attachment/{policy_target,policy_target_type}.py` → `TM/application/domain/model/shared/`;
  - `TM/application/domain/service/table_maintenance_policy_attachment/{candidate_policy_targets,enclosing_policy_targets}.py` → `TM/application/domain/service/shared/`. Delete the emptied domain-service package;
  - `TM/application/service/table_maintenance_policy_attachment/{policy_target_from_request,scope_target_in_listing}.py` → `TM/application/service/shared/`;
  - the target DTOs of `TM/adapter/inbound/web/table_maintenance_policy_attachment/dto.py` (`PolicyTargetApiRequest`, `DetachPolicyTargetApiRequest`, `PolicyTargetApiResponse` and their `type` literal) → `TM/adapter/inbound/web/shared/dto.py`.
- Create:
  - `TM/application/domain/model/shared/checked_policy_name.py`;
  - `TM/application/domain/service/shared/nearest_attached.py`;
  - `TM/application/service/shared/target_in_catalog.py`, the body of `ListTableMaintenancePolicyAttachmentsService._in_catalog` and `_table_in_catalog`;
  - `TM/application/port/outbound/table/read_table_metadata/catalog_access_denied_error.py`.
- Modify:
  - every importer (`grep -rn "PolicyTarget\|candidate_policy_targets\|enclosing_policy_targets\|policy_target_from_request\|scope_target_in_listing" src/data-platform/backend`). Port packages that re-export the target keep re-exporting it from its new place;
  - `table_maintenance_policy_name.py`, which calls the checker;
  - `notify_policy_change.py` and `resolve_applicable_table_maintenance_policy.py`, which use `nearest_attached`;
  - `list_table_maintenance_policy_attachments.py`, which uses `target_in_catalog`;
  - `PolicyTargetType`'s docstring: "a policy", not "a maintenance policy";
  - `TM/application/port/outbound/table/read_table_metadata/gateway.py` (two methods) and `__init__.py`;
  - `TM/adapter/outbound/table/pyiceberg/read_table_metadata_pyiceberg_gateway.py`;
  - `tests/.../fakes/fake_read_table_metadata_gateway.py`, which gains `add_catalog(name)`, `add_namespace(catalog, namespace)` and `deny(catalog)`;
  - `TM/adapter/inbound/web/error_handlers.py` (`CatalogAccessDeniedError` → 403);
  - `TM/adapter/inbound/event_consumer/consumer_loop.py`, which drops a hint on `CatalogAccessDeniedError` as on `CatalogNotFoundError`;
  - `tests/architecture/test_outbound_port_structure.py` (`GATEWAY_EXTRA_FILES` adds `catalog_access_denied_error.py`) and `test_service_structure.py` (`UTILITY_FILES` adds `target_in_catalog.py`).
- Test:
  - the moved tests go to the mirrored `shared` paths;
  - new tests `tests/.../domain/service/shared/test_nearest_attached.py` and `tests/.../domain/model/shared/test_checked_policy_name.py`;
  - the PyIceberg gateway test and `tests/.../application/service/table_maintenance_policy_attachment/test_attachment_services.py`.

**Interfaces:**
- Consumes (at HEAD): `PolicyTarget.key()`, the attachment services, and `ReadTableMetadataPyIcebergGateway._open`, whose bare `RESTError` is `CatalogNotFoundError`.
- Produces:
  - From `TM.application.domain.model.shared`: `PolicyTarget`, `PolicyTargetType`, and `checked_policy_name(value: str) -> str`, which raises `ValueError` with today's two messages and builds the id test from `shared_kernel.prefixed_id_pattern`.
  - From `TM.application.domain.service.shared`:
    - `candidate_policy_targets(name: TableName, table_uuid: str) -> tuple[PolicyTarget, ...]`;
    - `enclosing_policy_targets(catalog: str, namespace: str | None) -> tuple[PolicyTarget, ...]`;
    - `nearest_attached[T](candidates: Sequence[PolicyTarget], attached: Mapping[str, T]) -> tuple[PolicyTarget, T] | None`, keyed by `PolicyTarget.key()`.
  - `ReadTableMetadataGateway` gains:
    - `catalog_exists(catalog: str) -> bool`, which opens the catalog and is `False` on `CatalogNotFoundError`;
    - `namespace_exists(catalog: str, namespace: str) -> bool`, the dot-joined namespace through PyIceberg's `namespace_exists`.
    - Both raise `CatalogAccessDeniedError`.
  - `class CatalogAccessDeniedError(Exception)`, with `__init__(self, catalog: str)`, message `the platform's catalog credential cannot read catalog <name>`, and `.catalog`. The PyIceberg gateway raises it for `ForbiddenError` and `UnauthorizedError` from opening, listing and loading.
  - `policy_target_from_request(gateway, target_type, path, table_uuid=None, *, must_exist)` keeps its signature. With `must_exist` it checks a catalog with `catalog_exists` and a namespace with `namespace_exists`, so either may be empty. `CatalogAccessDeniedError` passes through untouched (403).
  - `target_in_catalog(target: PolicyTarget, gateway: ReadTableMetadataGateway, tables_repo: TablesRepo) -> bool` decides "orphaned". A table counts as in the catalog when it is known and not dropped, or loads under its path with the same uuid; a catalog or namespace counts when the existence check says so.
  - `scope_target_in_listing` is deleted once nothing calls it.

- [ ] **Step 1: Write the failing tests**

```python
def test_nearest_attached_prefers_the_first_candidate_that_is_attached():
    table, ns, catalog = candidate_policy_targets(TableName(catalog="iceberg", namespace="sales", table="orders"), "u1")
    assert nearest_attached((table, ns, catalog), {ns.key(): "A", catalog.key(): "B"}) == (ns, "A")

def test_nearest_attached_is_none_when_nothing_is_attached(): ...   # {} → None
def test_checked_policy_name_refuses_an_id_shaped_name(): ...       # "dp-01h2xcejqtf2nbrexx3vqjhp41" → ValueError
def test_checked_policy_name_refuses_a_space(): ...                 # "a b" → ValueError

# test_attachment_services.py (maintenance, behaviour change)
def test_attach_to_an_empty_catalog(attach, catalog): ...           # catalog.add_catalog("empty"); attach → stored
def test_attach_to_an_empty_namespace(attach, catalog): ...         # catalog.add_namespace("iceberg", "new"); stored
def test_attach_to_a_missing_namespace_is_not_found(attach): ...    # NotFoundError, nothing stored
def test_attach_in_a_refused_catalog_is_access_denied(attach, catalog):
    catalog.deny("secret")
    with pytest.raises(CatalogAccessDeniedError, match="cannot read catalog secret"):
        attach.execute(AttachTableMaintenancePolicyUseCaseInput(target_type="catalog", path=("secret",), policy_name="p"))

# the PyIceberg gateway test
def test_forbidden_on_open_is_access_denied(): ...                   # factory raising ForbiddenError → CatalogAccessDeniedError
def test_namespace_exists_reads_the_dotted_namespace(): ...         # "sales.eu" → namespace_exists(("sales", "eu"))
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance -k "nearest_attached or checked_policy_name or empty_catalog or empty_namespace or missing_namespace or refused_catalog or forbidden_on_open or namespace_exists" -v`. Expected: FAIL; import errors, and `NotFoundError` for the empty catalog.
- [ ] **Step 3: Implement the moves**, with no shims, then the new functions and the existence check. `<generate>`, then `git -C /Users/kcl/Projects/retail-lakehouse diff --stat -- src/data-platform/backend/openapi.json` prints nothing (the DTO classes keep their names).
- [ ] **Step 4: Run and watch them pass:** the same command, then `<pytest> -q`.
- [ ] **Step 5: Gate and commit.** `<gate> backend`; commit `refactor(table-maintenance): move policy targets and the nearest-attachment walk to shared (KCL-71)`.

### Task 2: The `TableDiscoveryPolicy` aggregate

**Files:**
- Create in `DP/`:
  - the ids and constants: `table_discovery_policy_id.py`, `default_discovery_policy_id.py`, `default_discovery_policy_name.py`, `table_discovery_policy_name.py`;
  - the enums: `discovery_outcome.py`, `discovery_attribute.py`, `condition_operator.py`;
  - the content: `discovery_condition.py`, `table_discovery_rule.py`, `discovery_match.py`, `discovery_decision.py`, `discovery_policy_content.py`;
  - the aggregate and its version: `table_discovery_policy_version.py`, `table_discovery_policy.py`;
  - the errors: `stale_discovery_policy_version.py`, `default_discovery_policy_is_fixed.py`;
  - `__init__.py`.
- Move into `DP/`: `TM/application/domain/model/table_discovery_rules/{table_discovery_rule_id,unknown_discovery_rule_id}.py`. The old package re-exports them until Task 14.
- Delete `table_discovery_rules_id.py`. The old aggregate's `id` becomes `TableDiscoveryPolicyId`, and `GLOBAL_TABLE_DISCOVERY_RULES_ID` an alias of `DEFAULT_DISCOVERY_POLICY_ID` until Task 14, because `tests/architecture/test_prefixed_ids.py` refuses `dp` on two classes.
- Create: `TM/application/port/outbound/table_discovery_policy/{__init__,table_discovery_policies_repo}.py`, the abstract port only. Every aggregate needs one repository port, and Task 4 implements it.
- Modify:
  - `TM/application/domain/model/table/table.py`, which imports `TableDiscoveryRuleId` from `DP`;
  - `tests/architecture/test_prefixed_ids.py`: the `TableDiscoveryRulesId` row becomes `TableDiscoveryPolicyId: "dp"`;
  - `tests/architecture/test_aggregates.py`, which adds `table_discovery_policy`;
  - `TM/application/service/shared/translate_domain_errors.py`, where `StaleDiscoveryPolicyVersion` and `DefaultDiscoveryPolicyIsFixed` → `ConflictError`.
- Test: `tests/.../domain/model/table_discovery_policy/{test_discovery_policy_content,test_table_discovery_policy}.py`.

**Interfaces:**
- Consumes: `checked_policy_name` (Task 1), `TableName`.
- Produces:
  - Ids and constants:
    - `TableDiscoveryPolicyId(EntityId)`, with `PREFIX = "dp"`;
    - `DEFAULT_DISCOVERY_POLICY_ID = TableDiscoveryPolicyId("dp-00000000000000000000000000")`;
    - `DEFAULT_DISCOVERY_POLICY_NAME = "default"`;
    - `TableDiscoveryPolicyName(ValueObject)`, whose `value: str` is checked by `checked_policy_name`.
  - The enums:
    - `DiscoveryOutcome(StrEnum)`: `MANAGE = "manage"`, `UNMANAGE = "unmanage"`;
    - `DiscoveryAttribute(StrEnum)`: `NAMESPACE = "namespace"`, `TABLE_NAME = "table_name"`;
    - `ConditionOperator(StrEnum)`: `GLOB = "glob"`.
  - The content:
    - `DiscoveryCondition(ValueObject)`: `attribute`, `operator`, `values: tuple[str, ...]`, and `matches(name: TableName) -> bool`.
    - `TableDiscoveryRule(ValueObject)`: `id: TableDiscoveryRuleId`, `outcome: DiscoveryOutcome`, `conditions: tuple[DiscoveryCondition, ...]`, and `matches(name) -> bool`, true when every condition holds.
    - `DiscoveryMatch(ValueObject)`: `policy_id: TableDiscoveryPolicyId`, `policy_version: PositiveInt`, `rule_id: TableDiscoveryRuleId | None`.
    - `DiscoveryDecision(ValueObject)`: `outcome: DiscoveryOutcome`, `match: DiscoveryMatch`, and the property `manages -> bool`.
    - `DiscoveryPolicyContent(ValueObject)`:
      - fields `description: str = ""`, `rules: tuple[TableDiscoveryRule, ...] = ()`, `no_match_outcome: DiscoveryOutcome`;
      - `platform_default()`, a classmethod giving the default's content;
      - `deciding_rule(name) -> TableDiscoveryRule | None`;
      - `can_manage() -> bool`;
      - `rule_ids() -> frozenset[TableDiscoveryRuleId]`.
      - Its wire form is exactly the JSON of Global Constraints (`from_primitives` / `to_primitives`).
  - The aggregate and its version:
    - `TableDiscoveryPolicyVersion(ValueObject)`: `policy_id`, `version: PositiveInt`, `content`, `created_at`.
    - `TableDiscoveryPolicy(AggregateRoot[TableDiscoveryPolicyId])`:
      - fields `id`, `name`, `content`, `version: PositiveInt`, `created_at`, `updated_at`;
      - `create(name, content, now)`, a new `dp-` id at version 1, refusing any rule id (`UnknownDiscoveryRuleId`);
      - `create_default(now)`;
      - `replace(content, expected_version: int, now) -> None`. It refuses the default first (`DefaultDiscoveryPolicyIsFixed`), then a stale version (`StaleDiscoveryPolicyVersion`), then any rule id outside the current version's `rule_ids()` plus the ids the caller minted for this request. It takes those minted ids as `new_rule_ids: Collection[TableDiscoveryRuleId] = ()`;
      - `current_version() -> TableDiscoveryPolicyVersion`;
      - the property `is_default`;
      - `decide(name) -> DiscoveryDecision`, which uses the deciding rule's outcome, or `no_match_outcome` with `rule_id=None`, and the policy's own id and version;
      - `can_manage()`, which delegates to the content.
  - The errors: `StaleDiscoveryPolicyVersion(ValueError)`, `DefaultDiscoveryPolicyIsFixed(ValueError)`, `UnknownDiscoveryRuleId(ValueError)` (moved).
  - The port `TableDiscoveryPoliciesRepo(Repository[TableDiscoveryPolicy])`:
    - `get_by_name(name: TableDiscoveryPolicyName) -> TableDiscoveryPolicy | None`;
    - `get_many(ids: Sequence[EntityId]) -> list[TableDiscoveryPolicy]`;
    - `update(policy) -> TableDiscoveryPolicy`, which writes the version row in the same transaction and raises `StaleDiscoveryPolicyVersion` when the stored version is not `policy.version - 1`;
    - `get_version(policy_id: EntityId, version: int) -> TableDiscoveryPolicyVersion | None`;
    - `delete(entity_id) -> None`, `ConflictError` while attached;
    - a `create` of a taken name is `ConflictError`.

- [ ] **Step 1: Write the failing tests**

```python
R1, R2 = "dr-00000000000000000000000001", "dr-00000000000000000000000002"
ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders_tmp")

def _rule(rule_id, outcome, **globs):  # globs: namespace=[...], table_name=[...]
    return {"id": rule_id, "outcome": outcome,
            "conditions": [{"attribute": a, "operator": "glob", "values": v} for a, v in globs.items()]}

def _content(no_match="unmanage", *rules):
    return DiscoveryPolicyContent.from_primitives({"no_match_outcome": no_match, "rules": list(rules)})

def test_the_first_matching_rule_decides():
    policy = TableDiscoveryPolicy.create(NAME, _content("unmanage"), T0)
    policy.replace(_content("unmanage", _rule(R1, "manage", table_name=["orders_tmp"]),
                            _rule(R2, "unmanage", table_name=["*_tmp"])), 1, T1, new_rule_ids={RID1, RID2})
    assert policy.decide(ORDERS) == DiscoveryDecision(
        outcome=DiscoveryOutcome.MANAGE, match=DiscoveryMatch(policy_id=policy.id, policy_version=2, rule_id=RID1))

def test_no_match_uses_the_no_match_outcome_without_a_rule(): ...   # rules (), "manage" → (MANAGE, rule_id None)
def test_every_condition_must_hold(): ...                            # namespace ["sales"] + table_name ["orders_*"] misses "sales.eu"
def test_namespace_glob_crosses_dots(): ...                           # ["sales.*"] matches "sales.eu"
def test_glob_is_case_sensitive(): ...                                # ["Orders*"] misses "orders_tmp"
def test_a_rule_needs_a_condition(): ...                              # conditions [] → InvariantViolation
def test_an_attribute_appears_once_per_rule(): ...                    # two table_name conditions → InvariantViolation
def test_empty_values_or_an_empty_glob_are_refused(): ...             # [] and [""] → InvariantViolation
def test_unknown_attribute_or_operator_is_refused(): ...              # "label", "regex" → InvariantViolation
def test_rule_ids_are_unique(): ...                                   # same id twice → InvariantViolation
def test_can_manage(): ...  # default False; one manage rule True; no rules + "manage" True; only unmanage + "unmanage" False
def test_content_round_trips_its_wire_form(): ...                     # to_primitives(from_primitives(x)) == x

def test_replace_refuses_an_id_the_policy_does_not_hold():
    policy = TableDiscoveryPolicy.create(NAME, _content(), T0)
    with pytest.raises(UnknownDiscoveryRuleId, match=R2):
        policy.replace(_content("unmanage", _rule(R2, "manage", table_name=["*"])), 1, T1)
    assert policy.version == 1
def test_create_refuses_any_rule_id(): ...                            # create with R1 → UnknownDiscoveryRuleId
def test_replace_refuses_a_stale_version(): ...                       # expected 3 at version 1 → StaleDiscoveryPolicyVersion
def test_the_default_cannot_be_replaced(): ...                        # create_default(T0).replace(...) → DefaultDiscoveryPolicyIsFixed
def test_the_default_has_its_fixed_id_name_and_content(): ...         # is_default, "default", no rules, unmanage, description
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain/model/table_discovery_policy -v`. Expected: FAIL; the package cannot be imported.
- [ ] **Step 3: Implement.** `DiscoveryCondition.matches` reads `name.namespace` or `name.table` by attribute, then `any(fnmatchcase(value, glob) for glob in self.values)`.
- [ ] **Step 4: Run and watch them pass:** the same command, then `<pytest> tests/architecture -q`.
- [ ] **Step 5: Gate and commit.** `<gate> backend`; commit `feat(table-maintenance): add the versioned discovery policy aggregate (KCL-71)`.

### Task 3: The attachment aggregate and how a table resolves

**Files:**
- Create:
  - `DA/{__init__,table_discovery_policy_attachment_id,table_discovery_policy_attachment}.py`;
  - `TM/application/domain/service/table_discovery_policy_attachment/{__init__,decide_table_discovery,scanned_catalogs}.py`;
  - `TM/application/port/outbound/table_discovery_policy_attachment/{__init__,table_discovery_policy_attachments_repo}.py`, the abstract port only.
- Modify: `tests/architecture/test_prefixed_ids.py` (`TableDiscoveryPolicyAttachmentId: "da"`) and `tests/architecture/test_aggregates.py` (adds `table_discovery_policy_attachment`).
- Test: `tests/.../domain/model/table_discovery_policy_attachment/test_table_discovery_policy_attachment.py`, and `tests/.../domain/service/table_discovery_policy_attachment/{test_decide_table_discovery,test_scanned_catalogs}.py`.

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces:
  - `TableDiscoveryPolicyAttachmentId(EntityId)`, with `PREFIX = "da"`.
  - `TableDiscoveryPolicyAttachment(AggregateRoot[TableDiscoveryPolicyAttachmentId])`:
    - fields `id`, `target: PolicyTarget`, `policy_id: TableDiscoveryPolicyId`, `attached_at`;
    - `attach(target, policy_id, now)`, under a new `da-` id;
    - `replace_policy(policy_id, now)`;
    - the property `catalog -> str`, which is `target.path[0]`.
  - `decide_table_discovery(name: TableName, table_uuid: str, attachments: Iterable[TableDiscoveryPolicyAttachment], policies: Mapping[TableDiscoveryPolicyId, TableDiscoveryPolicy]) -> DiscoveryDecision`:
    - `nearest_attached(candidate_policy_targets(name, table_uuid), …)` over the attachments whose policy is in `policies`, and that policy decides;
    - with no such attachment, the default decides: its fixed content, `DEFAULT_DISCOVERY_POLICY_ID`, version 1.
  - `scanned_catalogs(attachments: Iterable[TableDiscoveryPolicyAttachment], policies: Mapping[TableDiscoveryPolicyId, TableDiscoveryPolicy]) -> tuple[str, ...]`: the sorted, unique catalogs of the attachments whose policy `can_manage()`.
  - `TableDiscoveryPolicyAttachmentsRepo(Repository[TableDiscoveryPolicyAttachment])`:
    - `get_by_target(target)`;
    - `get_many_by_targets(targets)`;
    - `list_in_catalog(catalog: str) -> list[...]`;
    - `list_all() -> list[...]`, which `scanned_catalogs` reads in Tasks 8 and 9;
    - `list_for_policy(policy_id) -> list[...]`;
    - `has_attachments_for_policy(policy_id) -> bool`;
    - `update(attachment)`;
    - `delete(entity_id)`.
    - A second `create` on the same `target.key()` is `ConflictError`.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_table_attachment_beats_a_managing_catalog():
    decision = decide_table_discovery(ORDERS, "u1",
        [attached(catalog_target("iceberg"), MANAGE_ALL), attached(table_target(ORDERS, "u1"), DEFAULT)],
        {MANAGE_ALL.id: MANAGE_ALL, DEFAULT.id: DEFAULT})
    assert (decision.outcome, decision.match.policy_id) == (DiscoveryOutcome.UNMANAGE, DEFAULT_DISCOVERY_POLICY_ID)

def test_the_deepest_namespace_wins(): ...           # "sales" manage, "sales.eu" unmanage → unmanage for sales.eu.orders
def test_nothing_attached_is_the_default_v1(): ...   # [] → (UNMANAGE, DiscoveryMatch(dp-0…0, 1, None))
def test_a_table_is_found_by_uuid_not_by_path(): ... # table target path of an old name, same uuid → its policy decides
def test_an_attachment_without_its_policy_is_skipped(): ...  # catalog's policy missing from policies → the namespace's decides

def test_a_catalog_is_scanned_when_a_policy_in_it_can_manage():
    assert scanned_catalogs(
        [attached(namespace_target("iceberg", "sales"), MANAGE_ALL), attached(catalog_target("other"), DEFAULT)],
        {MANAGE_ALL.id: MANAGE_ALL, DEFAULT.id: DEFAULT},
    ) == ("iceberg",)
def test_scanned_catalogs_are_sorted_and_unique(): ...
def test_replace_policy_keeps_the_attachment_id(): ...
```

  `attached`, `catalog_target`, `namespace_target`, `table_target`, `MANAGE_ALL` and `DEFAULT` are module helpers of the test file. `MANAGE_ALL` has one rule managing `table_name ["*"]`.
- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/domain -k "discovery_policy_attachment or decide_table_discovery or scanned_catalogs" -v`. Expected: FAIL; not importable.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass:** the same command.
- [ ] **Step 5: Gate and commit.** `<gate> backend`; commit `feat(table-maintenance): add discovery policy attachments and resolve the nearest one (KCL-71)`.

### Task 4: Store discovery policies and attachments, and seed the default

**Files:**
- Create:
  - `TM/adapter/outbound/table_discovery_policy/sql/{__init__,table_discovery_policies_table,table_discovery_policy_versions_table,table_discovery_policy_row_mapper,table_discovery_policies_sql_repo}.py`, plus the package `__init__`;
  - `TM/adapter/outbound/table_discovery_policy_attachment/sql/{__init__,table_discovery_policy_attachments_table,table_discovery_policy_attachment_row_mapper,table_discovery_policy_attachments_sql_repo}.py`, plus the package `__init__`;
  - `tests/context/table_maintenance/fakes/{in_memory_table_discovery_policies_repo,in_memory_table_discovery_policy_attachments_repo}.py`;
  - `TM/application/port/inbound/table_discovery_policy/ensure_default_table_discovery_policy/`;
  - `TM/application/service/table_discovery_policy/ensure_default_table_discovery_policy.py`.
- Modify:
  - `TM/adapter/outbound/shared/sql/create_schema.py`: `AGGREGATE_SQL_PACKAGES` adds both packages;
  - `bootstrap/container/{repositories,build_repositories}.py`, which add `table_discovery_policies` and `table_discovery_policy_attachments`;
  - `bootstrap/container/run_migrations.py`, which seeds the default discovery policy after the maintenance one and logs both.
- Test:
  - `tests/.../adapter/outbound/table_discovery_policy/test_table_discovery_policies_sql_repo.py`;
  - `tests/.../adapter/outbound/table_discovery_policy_attachment/test_table_discovery_policy_attachments_sql_repo.py`;
  - the drift test `tests/.../adapter/outbound/shared/sql/test_create_schema.py`;
  - `tests/bootstrap/container/test_run_migrations.py`;
  - `tests/.../application/service/table_discovery_policy/test_ensure_default_table_discovery_policy.py`.

**Interfaces:**
- Consumes: the two repository ports of Tasks 2 and 3. This task writes their SQL adapters and in-memory fakes, which follow the maintenance repos' transaction and `IntegrityError` handling.
- Produces:
  - The tables, as the maintenance ones are:
    - `table_discovery_policies`: `id` pk, `name` unique, `version`, `created_at`, `updated_at`;
    - `table_discovery_policy_versions`: `policy_id` fk and `version` as the pk, `content_json` JSON, `created_at`;
    - `table_discovery_policy_attachments`: `id` pk, `target_key` unique, `target_type`, `path_json`, `table_uuid` nullable, `catalog` indexed, `policy_id` fk indexed, `attached_at`.
  - `EnsureDefaultTableDiscoveryPolicyUseCase`, whose input is empty and whose output is `created: bool`. The service `EnsureDefaultTableDiscoveryPolicyService(policies_repo, *, clock=...)` creates the default when `get(DEFAULT_DISCOVERY_POLICY_ID)` is None.

- [ ] **Step 1: Write the failing tests.** They use SQLite through the existing repo-test engine fixture. The fakes run the same tests through a parametrised fixture, as the maintenance repos' do.

```python
def test_update_writes_a_version_and_keeps_the_old_one(repo): ...   # v1 and v2 both readable by get_version
def test_update_from_a_stale_copy_is_refused(repo): ...             # two copies, second update → StaleDiscoveryPolicyVersion
def test_a_taken_name_conflicts(repo): ...                          # ConflictError
def test_delete_while_attached_conflicts(repos): ...                # ConflictError, policy still there
def test_one_attachment_per_target(attachments): ...                # second create on the same key → ConflictError
def test_list_in_catalog_returns_only_that_catalog(attachments): ...
def test_a_table_target_round_trips_its_uuid(attachments): ...
def test_migrate_seeds_the_default_discovery_policy(): ...          # run_migrations, then get(DEFAULT_DISCOVERY_POLICY_ID).is_default
def test_ensure_default_twice_keeps_one(): ...                      # created True, then False
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/outbound/table_discovery_policy tests/context/table_maintenance/adapter/outbound/table_discovery_policy_attachment tests/bootstrap/container/test_run_migrations.py -v`. Expected: FAIL; the modules are missing.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass:** the same command, then the drift test.
- [ ] **Step 5: Gate and commit.** `<gate> backend`; commit `feat(table-maintenance): store discovery policies, their versions and attachments (KCL-71)`.

### Task 5: Discovery policy use cases and `/v1/discovery-policies`

**Files:**
- Create:
  - under `TM/application/port/inbound/table_discovery_policy/`: `create_table_discovery_policy/`, `get_table_discovery_policy/`, `list_table_discovery_policies/`, `update_table_discovery_policy/`, `delete_table_discovery_policy/` and `get_table_discovery_policy_version/`, each with `__init__`, `input`, `output` and `use_case`;
  - under `TM/application/service/table_discovery_policy/`: one service per package, plus `table_discovery_policy_output_fields.py` and `content_with_minted_rule_ids.py`;
  - `TM/adapter/inbound/web/table_discovery_policy/{__init__,dto,router}.py`.
- Modify:
  - `TM/adapter/inbound/web/{register_routes.py,shared/web_use_cases.py}`;
  - `bootstrap/container/{use_cases,build_use_cases,build_web_use_cases}.py`;
  - `tests/architecture/test_service_structure.py` (`UTILITY_FILES`);
  - `openapi.json` and the generated client (`<generate>`).
- Test: `tests/.../application/service/table_discovery_policy/test_table_discovery_policy_services.py` and `tests/.../adapter/inbound/web/table_discovery_policy/test_table_discovery_policy_routes.py`, on a new `DiscoveryPolicyWebWorld` beside `PolicyWebWorld` in `tests/.../adapter/inbound/web/discovery_policy_web_world.py`.

**Interfaces:**
- Consumes: Task 4.
- Produces:
  - Inputs:
    - `CreateTableDiscoveryPolicyUseCaseInput(name: str, content: dict[str, Any])`;
    - `GetTableDiscoveryPolicyUseCaseInput(name: str)`;
    - `ListTableDiscoveryPoliciesUseCaseInput()`;
    - `UpdateTableDiscoveryPolicyUseCaseInput(name: str, content: dict[str, Any], version: int)`;
    - `DeleteTableDiscoveryPolicyUseCaseInput(name: str)`;
    - `GetTableDiscoveryPolicyVersionUseCaseInput(name: str, version: int)`.
    - `content` is the JSON of Global Constraints, and a rule may omit `id`.
  - Outputs carry `id`, `name`, `is_default`, `version`, `content: dict[str, Any]`, `created_at` and `updated_at`.
    - The version output has the version's `created_at` and no `updated_at`.
    - The list output's nested `TableDiscoveryPolicy` adds `attachment_count: int`, from one `list_for_policy` per policy.
  - `content_with_minted_rule_ids(content: dict[str, Any], new_id: Callable[[], str]) -> tuple[dict[str, Any], frozenset[str]]`. It gives each rule whose `id` is absent or `None` a minted `dr-` id, and returns the ids it minted.
    - A rule whose `id` is `""` raises `ValueError("a rule id is a dr- id or absent")` (422).
  - Update service: it builds the content, calls `policy.replace(content, version, now, new_rule_ids=…)` and `policies_repo.update`. Task 9 adds what follows the save; this task saves only.
  - Routes, whose function names are the operation ids:
    - `list_table_discovery_policies` `GET /discovery-policies` → `TableDiscoveryPoliciesApiResponse{policies: list[ListedTableDiscoveryPolicyApiResponse]}`;
    - `create_table_discovery_policy` `POST` (201), body `CreateTableDiscoveryPolicyApiRequest{name, description = "", no_match_outcome, rules}`;
    - `get_table_discovery_policy`, `update_table_discovery_policy` (`UpdateTableDiscoveryPolicyApiRequest{version, description, no_match_outcome, rules}`) and `delete_table_discovery_policy` (204) on `/discovery-policies/{name}`;
    - `get_table_discovery_policy_version` on `/discovery-policies/{name}/versions/{version}` → `TableDiscoveryPolicyVersionApiResponse`.
  - DTOs:
    - `TableDiscoveryPolicyApiResponse{id, name, is_default, version, created_at, updated_at, description, no_match_outcome, rules: list[DiscoveryRuleApiResponse]}`;
    - `DiscoveryRuleApiRequest{id: str | None = None, outcome: Literal["manage", "unmanage"], conditions: list[DiscoveryConditionApiRequest]}`;
    - `DiscoveryConditionApiRequest{attribute: Literal["namespace", "table_name"], operator: Literal["glob"], values: list[str]}`;
    - and their `…ApiResponse` twins.
    - The router flattens `content` into the body, as `_policy_response` does for maintenance.

- [ ] **Step 1: Write the failing tests**

```python
def test_create_mints_rule_ids_and_starts_at_version_1(world): ...   # every rules[i]["id"] matches ^dr-, version 1
def test_create_with_a_taken_name_conflicts(world): ...
def test_update_keeps_the_ids_it_was_sent_and_bumps_the_version(world): ...
def test_update_with_another_policys_rule_id_is_refused(world):
    other = world.create("other", one_rule())
    with pytest.raises(ValidationError, match="unknown discovery rule id"):
        world.update("mine", version=1, content=content_with_rule_id(other.content["rules"][0]["id"]))
    assert world.get("mine").version == 1
def test_update_from_a_stale_version_conflicts(world): ...
def test_update_of_the_default_conflicts(world): ...
def test_delete_of_the_default_or_an_attached_policy_conflicts(world): ...
def test_a_version_stays_readable_after_an_update(world): ...        # get_version(name, 1) is the old content
def test_list_counts_attachments(world): ...

def test_post_then_get_round_trips_the_body(client): ...             # rule order and conditions unchanged
def test_put_with_an_empty_rule_id_is_422(client): ...               # detail "a rule id is a dr- id or absent"
def test_put_with_two_table_name_conditions_is_422(client): ...
def test_put_default_is_409(client): ...
def test_get_unknown_policy_is_404(client): ...
def test_get_version_0_is_404(client): ...
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/service/table_discovery_policy tests/context/table_maintenance/adapter/inbound/web/table_discovery_policy -v`. Expected: FAIL.
- [ ] **Step 3: Implement**, mirroring the maintenance policy services and router. Names are checked through `TableDiscoveryPolicyName` inside `translate_domain_errors`. Then `<generate>`.
- [ ] **Step 4: Run and watch them pass:** the same command, then `<pytest> -q`.
- [ ] **Step 5: Gate and commit.** `<gate> all` (the client changed); commit `feat(table-maintenance): create, edit and version discovery policies through the API (KCL-71)`.

### Task 6: Attach and detach discovery policies

**Files:**
- Create:
  - under `TM/application/port/inbound/table_discovery_policy_attachment/`: `attach_table_discovery_policy/`, `detach_table_discovery_policy/` and `list_table_discovery_policy_attachments/`;
  - the three services under `TM/application/service/table_discovery_policy_attachment/`;
  - `TM/adapter/inbound/web/table_discovery_policy_attachment/{__init__,dto,router}.py`.
- Modify: the wiring files of Task 5, `openapi.json` and the client.
- Test: `tests/.../application/service/table_discovery_policy_attachment/test_discovery_attachment_services.py` and `tests/.../adapter/inbound/web/table_discovery_policy_attachment/test_discovery_attachment_routes.py`.

**Interfaces:**
- Consumes: Tasks 1, 3, 4 and 5. `policy_target_from_request` and `target_in_catalog` come from `service/shared`.
- Produces:
  - `AttachTableDiscoveryPolicyUseCaseInput(policy_name: str, target_type: str, path: tuple[str, ...])`. Its output is `(id, target_type, path, table_uuid, policy_id, policy_name, attached_at)`.
    - The target must exist (`must_exist=True`), and attaching replaces what the target held, keeping that attachment's id.
  - `DetachTableDiscoveryPolicyUseCaseInput(policy_name: str, attachment_id: str)`, with an empty output.
    - A malformed id is `ValidationError`.
    - An unknown id, or one attached to another policy, is `NotFoundError` (`policy <name> has no attachment <id>`).
  - `ListTableDiscoveryPolicyAttachmentsUseCaseInput(policy_name: str)`. Its items are `(id, type, path, table_uuid, policy_id, policy_name, attached_at, orphaned)`, where `orphaned` is `not target_in_catalog(...)`.
  - Routes, tagged `discovery-policies`, on `/discovery-policies/{name}/attachments`:
    - `list_table_discovery_policy_attachments`;
    - `attach_table_discovery_policy` (PUT, 200);
    - `detach_table_discovery_policy` (`DELETE …/attachments/{attachment_id}`, 204).
  - DTOs:
    - `AttachTableDiscoveryPolicyApiRequest{target: PolicyTargetApiRequest}`;
    - `TableDiscoveryPolicyAttachmentApiResponse{id, target: PolicyTargetApiResponse, policy_id, policy_name, attached_at}`;
    - `ListedTableDiscoveryPolicyAttachmentApiResponse`, which adds `orphaned`;
    - `TableDiscoveryPolicyAttachmentsApiResponse{attachments}`.
  - Task 9 adds the schedule sync and the rescan around attach and detach. This task stores only.

- [ ] **Step 1: Write the failing tests**

```python
def test_attach_to_a_table_resolves_its_uuid_from_the_catalog(world): ...  # table_uuid set; the table need not be managed
def test_attach_replaces_the_targets_policy_and_keeps_the_id(world): ...
def test_attach_to_an_empty_catalog(world): ...                            # catalog.add_catalog("fresh") → stored
def test_attach_to_a_missing_namespace_is_not_found(world): ...
def test_attach_in_a_refused_catalog_is_access_denied(world): ...          # CatalogAccessDeniedError, nothing stored
def test_detach_by_id(world): ...                                          # gone from the list
def test_detach_of_another_policys_attachment_is_not_found(world):
    a = world.attach("other", "catalog", ("iceberg",))
    with pytest.raises(NotFoundError, match=f"has no attachment {a.id}"):
        world.detach("mine", a.id)
    assert world.list("other").items[0].id == a.id
def test_detach_works_for_an_orphaned_target(world): ...                   # catalog dropped from the fake → detach still 204
def test_list_marks_a_target_that_left_the_catalog_orphaned(world): ...

def test_put_attachment_in_a_refused_catalog_is_403(client): ...          # detail names the catalog
def test_delete_with_a_malformed_id_is_422(client): ...                    # "pa-…" or "x"
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/service/table_discovery_policy_attachment tests/context/table_maintenance/adapter/inbound/web/table_discovery_policy_attachment -v`. Expected: FAIL.
- [ ] **Step 3: Implement**, then `<generate>`.
- [ ] **Step 4: Run and watch them pass:** the same command.
- [ ] **Step 5: Gate and commit.** `<gate> all`; commit `feat(table-maintenance): attach discovery policies to catalogs, namespaces and tables (KCL-71)`.

### Task 7: Scans decide by the nearest discovery policy, and the table records the decision

**Files:**
- Create: `TM/application/service/table/discovery_decider.py`, added to `UTILITY_FILES`.
- Modify:
  - `TM/application/domain/model/table/{table,table_management_change}.py`;
  - `TM/application/domain/service/table/decide_table_management.py`;
  - `TM/application/service/table/{register_discovered_table,apply_discovery_to_known_table,sync_discovered_tables,process_table_hint,table_output_fields}.py`;
  - the table ports `get_table/output.py` and `list_tables/output.py`;
  - `TM/adapter/outbound/table/sql/{tables_table,table_row_mapper}.py`, which add the columns `matched_policy_id` and `matched_policy_version`;
  - `TM/adapter/inbound/web/table/dto.py`;
  - `bootstrap/container/build_use_cases.py`: the sync and hint services get the two discovery repos instead of the rules repo;
  - `openapi.json` and the client;
  - the console files `tsc` needs, which add `matched_policy_id` and `matched_policy_version` to every `TableApiResponse` literal: `FE/test/fixtures.ts`, `FE/stories/storyData.ts`, `FE/pages/TablePage.stories.tsx` and `FE/pages/TableListPage.test.tsx` (`grep -rln matched_rule_id src/data-platform/frontend/src | grep -v generated`).
- Test:
  - `tests/.../domain/model/table/test_table.py` and `tests/.../domain/service/table/test_decide_table_management.py`;
  - `tests/.../application/service/table/test_discovery_sync_services.py`. Its `_rule`, `_include_all` and `_exclude_all` helpers become `_attach(world, target, policy)` over a `MANAGE_ALL` and an `UNMANAGE_ALL` policy;
  - `tests/context/table_maintenance/application/service/conftest.py`, whose `rules_repo` fixture becomes `discovery_policies` and `discovery_attachments`;
  - the table route tests.

**Interfaces:**
- Consumes: Tasks 2, 3 and 4.
- Produces:
  - `Table`:
    - `discovered_by: DiscoveryMatch` replaces the stored `matched_rule_id`, and the property `matched_rule_id -> TableDiscoveryRuleId | None` reads it;
    - `register(id, name, decision: DiscoveryDecision, now)` is managed or unmanaged by `decision.outcome`, and `register_unmanaged` is deleted;
    - `manage(match: DiscoveryMatch, now)` and `unmanage(match: DiscoveryMatch, now)` are each idempotent for an equal match.
  - `TableManagementChange.MATCH_CHANGED = "match_changed"` replaces `RULE_CHANGED`.
  - `decide_table_management(table: Table, decision: DiscoveryDecision, now: datetime) -> TableManagementChange` returns `MANAGED`, `UNMANAGED`, `MATCH_CHANGED` (management the same, the match moved, managed or not) or `UNCHANGED`. `apply_discovery_to_known_table` saves the row on any change but `UNCHANGED`.
  - `class DiscoveryDecider`:
    - `for_catalog(cls, catalog: str, attachments_repo: TableDiscoveryPolicyAttachmentsRepo, policies_repo: TableDiscoveryPoliciesRepo) -> DiscoveryDecider` reads one `list_in_catalog` and one `get_many`;
    - `for_table(cls, name: TableName, table_uuid: str, attachments_repo, policies_repo) -> DiscoveryDecider` reads one `get_many_by_targets(candidate_policy_targets(name, table_uuid))` and one `get_many`;
    - `decide(name: TableName, table_uuid: str) -> DiscoveryDecision` calls `decide_table_discovery`.
  - `register_discovered_table(found, decision: DiscoveryDecision, tables_repo, table_change_gateway, now)` and `apply_discovery_to_known_table(table, name, decision: DiscoveryDecision, …)`. The caller decides with the table's current name and its uuid.
  - `SyncDiscoveredTablesService(tables_repo, discovery_policies_repo, discovery_attachments_repo, discoveries_repo, catalog_gateway, table_change_gateway, *, clock)` and `ProcessTableHintService(tables_repo, discovery_policies_repo, discovery_attachments_repo, catalog_gateway, table_change_gateway, discovery_request_gateway, *, clock)`.
  - The output fields and `TableApiResponse` gain `matched_policy_id: str` and `matched_policy_version: int`, and keep `matched_rule_id: str | None`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_namespace_policy_manages_its_tables_under_the_deciding_rule(sync, world): ...  # managed, matched_rule_id == R1
def test_a_table_policy_overrides_its_namespace(sync, world): ...                         # default on the table → unmanaged
def test_nothing_attached_registers_unmanaged_and_sends_nothing(sync, world): ...         # discovered_by == (dp-0…0, 1, None)
def test_managed_by_the_no_match_outcome_has_no_rule(sync, world): ...                    # matched_rule_id is None
def test_a_renamed_table_keeps_its_table_attachment(sync, world):
    world.attach(table_target(OLD_NAME, "u1"), MANAGE_ALL); world.catalog.rename("u1", namespace="other")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace=None))
    assert world.tables.get(TableId("u1")).is_managed and out.renamed == 1
def test_a_new_policy_version_moves_the_match_and_sends_nothing(sync, world): ...         # MATCH_CHANGED, row saved, no signal
def test_the_scan_reads_attachments_once_per_catalog(sync, world): ...                    # track_calls: one list_in_catalog
def test_a_hint_in_an_unscanned_catalog_registers_unmanaged(hint, world): ...             # action "registered", no table change
def test_the_table_route_names_the_deciding_policy(client): ...                           # matched_policy_id, matched_policy_version
```

  `world` is a fixture in the sync test file holding the fakes and `attach(target, policy)`. `track_calls` is the existing fake helper.
- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/application/service/table tests/context/table_maintenance/application/domain -v`. Expected: FAIL.
- [ ] **Step 3: Implement.** No scan reads the rules aggregate any more. It and its API stay until Task 14 because the console still calls them. Then `<generate>`, and update the console literals until `npm --prefix /Users/kcl/Projects/retail-lakehouse/src/data-platform/frontend run typecheck` passes.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q` and `<vitest>`.
- [ ] **Step 5: Gate and commit.** `<gate> all`; commit `feat(table-maintenance): decide each discovered table by its nearest discovery policy (KCL-71)`.

### Task 8: Record a catalog the scan cannot read, and list the scanned catalogs

**Files:**
- Create:
  - `TM/application/domain/model/catalog_discovery/{catalog_scan_failure,catalog_scan_failure_reason}.py`;
  - `TM/application/port/inbound/catalog_discovery/list_scanned_catalogs/`;
  - `TM/application/service/catalog_discovery/list_scanned_catalogs.py`;
  - `TM/adapter/inbound/web/catalog_discovery/{__init__,dto,router}.py`.
- Modify:
  - `TM/application/domain/model/catalog_discovery/catalog_discovery.py`;
  - `TM/adapter/outbound/catalog_discovery/sql/*`: `last_discovered_at` becomes nullable, and the table gains `failure_reason`, `failure_detail` and `failed_at`;
  - `tests/.../fakes/in_memory_catalog_discoveries_repo.py`;
  - `TM/application/service/table/sync_discovered_tables.py`, `TM/application/port/inbound/table/sync_discovered_tables/output.py`, and `list_tables.py` and `get_table.py`, which read a `None` last discovery;
  - the wiring, `openapi.json` and the client.
- Test: `tests/.../domain/model/catalog_discovery/test_catalog_discovery.py`, the catalog discoveries SQL repo test, `test_discovery_sync_services.py`, and `tests/.../adapter/inbound/web/catalog_discovery/test_scanned_catalogs_route.py`.

**Interfaces:**
- Consumes: Tasks 1, 3 and 7.
- Produces:
  - `CatalogScanFailureReason(StrEnum)`: `CANNOT_ACCESS = "cannot_access"`, `NOT_FOUND = "not_found"`.
  - `CatalogScanFailure(ValueObject)`: `reason`, `detail: str`, `failed_at: datetime`.
  - `CatalogDiscovery`:
    - `last_discovered_at: datetime | None` and `last_failure: CatalogScanFailure | None`. A validator holds at least one of them;
    - `failed(catalog, failure)` as a classmethod, beside `first`;
    - `record_failure(failure)`, forward-only by `failed_at`;
    - the property `current_failure -> CatalogScanFailure | None`, the failure when it is newer than `last_discovered_at`.
    - The SQL repo's `save` moves each of the two times forward on its own, never back.
  - `SyncDiscoveredTablesService.execute`:
    - It catches `CatalogAccessDeniedError` and `CatalogNotFoundError` from `list_tables`, records the failure at the scan's start time with the error text, and returns zero counts with `failure` set.
    - A `load_table` that raises `CatalogAccessDeniedError` counts in `skipped` and turns the drop pass off for that scan.
    - `SyncDiscoveredTablesUseCaseOutput` gains `failure: str | None = None`, the reason.
  - `ListScannedCatalogsUseCaseInput()` → `ListScannedCatalogsUseCaseOutput(catalogs: tuple[ScannedCatalog, ...])`.
    - Each `ScannedCatalog` holds `catalog`, `last_discovered_at: datetime | None` and `failure: Failure | None`, where `Failure` is `reason`, `detail` and `failed_at`.
    - It reads `scanned_catalogs(attachments_repo.list_all(), policies by id)`, joined with `discoveries_repo`.
  - The route `list_scanned_catalogs`, `GET /scanned-catalogs`, tagged `discovery-policies`, answers `ScannedCatalogsApiResponse{catalogs: list[ScannedCatalogApiResponse]}`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_refused_catalog_is_recorded_and_changes_nothing(sync, world):
    world.attach(catalog_target("iceberg"), MANAGE_ALL); world.catalog.deny("iceberg")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace=None))
    assert out.failure == "cannot_access" and out.dropped == 0
    assert world.discoveries.get(CatalogDiscoveryId("iceberg")).current_failure.reason is CatalogScanFailureReason.CANNOT_ACCESS
def test_a_later_good_scan_makes_the_failure_not_current(sync, world): ...      # deny, scan, allow, scan → current_failure None
def test_a_refused_table_is_skipped_and_nothing_is_dropped(sync, world): ...    # one table denied, one known table missing → dropped 0
def test_a_missing_catalog_is_recorded_not_found(sync, world): ...
def test_failure_and_success_times_move_forward_independently(repo): ...        # SQL: an older failure never overwrites a newer one

def test_scanned_catalogs_list_only_catalogs_a_policy_can_manage(client): ...   # default on "a", manage on "b.ns" → ["b"]
def test_scanned_catalogs_show_the_current_failure(client): ...                 # {"reason": "cannot_access", "detail": "...", "failed_at": ...}
```

- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance -k "refused or not_current or missing_catalog_is_recorded or independently or scanned_catalogs" -v`. Expected: FAIL.
- [ ] **Step 3: Implement**, then `<generate>`.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q`.
- [ ] **Step 5: Gate and commit.** `<gate> all`; commit `feat(table-maintenance): record a catalog discovery cannot read and list the scanned catalogs (KCL-71)`.

### Task 9: The scanned catalogs drive the schedules, and every change rescans

**Files:**
- Create:
  - `TM/application/port/outbound/table_discovery_policy_attachment/sync_discovery_schedules/{__init__,gateway,input}.py`;
  - `TM/adapter/hybrid/temporal/outbound/table_discovery_policy_attachment/{__init__,sync_discovery_schedules_temporal_gateway,table_discovery_schedule}.py`;
  - `TM/application/port/inbound/table_discovery_policy_attachment/sync_discovery_schedules/`;
  - `TM/application/service/table_discovery_policy_attachment/{sync_discovery_schedules,apply_discovery_change}.py`, with `apply_discovery_change.py` added to `UTILITY_FILES`;
  - `tests/context/table_maintenance/fakes/recording_sync_discovery_schedules_gateway.py`.
- Delete: `TM/adapter/hybrid/temporal/inbound/ensure_table_discovery_schedule.py` and its test. Its schedule body moves to `table_discovery_schedule.py`.
- Modify:
  - `TM/application/port/outbound/table/send_discovery_request/input.py`: `rules_version` → `change_id: str | None = None`;
  - `TM/adapter/hybrid/temporal/contracts/table_discovery/workflow_id.py` and `send_discovery_request_temporal_gateway.py`;
  - the update service of Task 5, and the attach and detach services of Task 6;
  - the old `replace_table_discovery_rules.py`, which sends `change_id=f"rules-v{version}"` until Task 14;
  - `bootstrap/container/{gateways,build_gateways,apply_worker_startup}.py` and `bootstrap/worker.py`.
- Test:
  - `tests/.../adapter/hybrid/temporal/outbound/table_discovery_policy_attachment/test_sync_discovery_schedules_temporal_gateway.py`, on the existing `TemporalHarness` (`harness` fixture), as the old ensure test was;
  - `tests/.../application/service/table_discovery_policy_attachment/test_apply_discovery_change.py`;
  - the workflow id test, `tests/bootstrap/container/test_apply_worker_startup.py`, `tests/bootstrap/test_worker.py` and `test_send_discovery_request_temporal_gateway.py`.

**Interfaces:**
- Consumes: Tasks 3 to 8.
- Produces:
  - `@dataclass(frozen=True) class SyncDiscoverySchedulesGatewayInput: catalogs: tuple[str, ...]`. `SyncDiscoverySchedulesGateway.sync(input) -> None` is abstract; afterwards exactly these catalogs have a discovery schedule.
  - `SyncDiscoverySchedulesTemporalGateway(client: Client, bridge: AsyncLoopBridge, *, interval: timedelta)`:
    1. lists the schedules (`client.list_schedules()`) whose id starts with `TABLE_DISCOVERY_SCHEDULE_ID_PREFIX`;
    2. creates each wanted one, or updates it and unpauses it, as today's create / `ScheduleAlreadyRunningError` → update / unpause does;
    3. deletes each listed one that is not wanted.
    - Temporal's schedule list is eventually consistent. A schedule just created may be missing from it, which only means it is not deleted, and no create depends on the listing.
  - `table_discovery_schedule(catalog: str, *, interval: timedelta) -> Schedule` is today's `_schedule`.
  - `SyncDiscoverySchedulesUseCaseInput()` → `SyncDiscoverySchedulesUseCaseOutput(catalogs: tuple[str, ...])`. `SyncDiscoverySchedulesService(policies_repo, attachments_repo, schedules: SyncDiscoverySchedulesGateway)` lets errors propagate.
  - `apply_discovery_change[T](policies_repo, attachments_repo, discovery_requests: SendDiscoveryRequestGateway, schedules: SyncDiscoverySchedulesGateway, change: Callable[[], T], *, affected_catalogs: Callable[[], Collection[str]], change_id: str) -> T`:
    1. `before = scanned_catalogs(...)`;
    2. `result = change()`. An exception here propagates, and nothing below runs;
    3. `after = scanned_catalogs(...)`;
    4. `schedules.sync(SyncDiscoverySchedulesGatewayInput(after))`, with an exception logged;
    5. for each catalog in `sorted(set(affected_catalogs()) & (set(before) | set(after)))`, send `SendDiscoveryRequestGatewayInput(catalog, None, change_id=change_id)`, each exception logged;
    6. return `result`.
  - The update, attach and detach services take `discovery_requests`, `schedules` and `new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex`.
    - Update's affected catalogs are `{a.catalog for a in attachments_repo.list_for_policy(policy.id)}`. Attach's and detach's are `{target.path[0]}`.
  - `table_discovery_adhoc_workflow_id(catalog, namespace, *, change_id: str | None = None)` gives `…:trigger=policy-changed:change={change_id}` when given and `…:trigger=adhoc` otherwise.
  - `apply_worker_startup(client, settings, use_cases)`. After the search-attribute check it runs `await asyncio.to_thread(use_cases.sync_discovery_schedules.execute, SyncDiscoverySchedulesUseCaseInput())`; the bridge would deadlock on its own loop thread. `run_worker` passes `use_cases`.
  - `build_gateways` adds `sync_discovery_schedules=SyncDiscoverySchedulesTemporalGateway(client, bridge, interval=timedelta(seconds=settings.discovery_interval_seconds))`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_sync_creates_wanted_and_deletes_unwanted_schedules(h):
    await h.create_discovery_schedule("old")
    await asyncio.to_thread(gateway(h).sync, SyncDiscoverySchedulesGatewayInput(catalogs=("iceberg",)))
    assert await h.schedule_ids("table-discovery:") == {"table-discovery:catalog=iceberg"}
async def test_sync_rewrites_the_interval_and_unpauses(h): ...
async def test_sync_leaves_other_schedules_alone(h): ...            # an unrelated schedule id survives

def test_detaching_the_last_managing_policy_rescans_and_drops_the_schedule(world):
    world.detach("manage-all", world.catalog_attachment_id)         # "iceberg" scanned before, not after
    assert world.schedules.synced[-1] == ()
    assert world.requests.sent == [SendDiscoveryRequestGatewayInput("iceberg", None, change_id=world.change_id)]
def test_attaching_an_unmanage_policy_in_an_unscanned_catalog_scans_nothing(world): ...  # synced (), sent []
def test_update_rescans_every_catalog_the_policy_is_attached_in(world): ...
def test_a_failed_schedule_sync_still_saves_and_rescans(world): ...                      # gateway raises; stored; request sent
def test_a_refused_update_neither_syncs_nor_rescans(world): ...                          # unknown rule id → ValidationError; synced [], sent []
def test_each_change_has_its_own_change_id(world): ...
def test_change_id_names_the_adhoc_workflow(): ...    # "table-discovery:catalog=iceberg:trigger=policy-changed:change=ab12"
async def test_worker_startup_syncs_the_discovery_schedules(): ...                       # use case called once, off the loop thread
async def test_worker_startup_fails_when_the_sync_fails(): ...
```

  `h.create_discovery_schedule` and `h.schedule_ids` are added to the test file, not to the shared harness. `world` is the fixture of `test_apply_discovery_change.py`, holding the real services on fakes, `RecordingSendDiscoveryRequestGateway` and the new recording schedules gateway.
- [ ] **Step 2: Run and watch them fail:** `<pytest> tests/context/table_maintenance/adapter/hybrid/temporal tests/context/table_maintenance/application/service/table_discovery_policy_attachment tests/bootstrap -v`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass:** the same command, including `tests/architecture/test_temporal_workflow_sandbox.py`, then `<pytest> -q`.
- [ ] **Step 5: Gate and commit.** `<gate> backend`; commit `feat(table-maintenance): scan the catalogs discovery policies can manage and rescan after each change (KCL-71)`.

### Task 10: Console: the Discovery policies list

**Files:**
- Create:
  - `FE/pages/DiscoveryPoliciesPage.tsx`, with `.stories.tsx` and `.test.tsx`;
  - `FE/components/CreateDiscoveryPolicyDialog.tsx`, with `.stories.tsx` and `.test.tsx`;
  - `FE/lib/discoveryPolicyPaths.ts`.
- Modify:
  - `FE/AppRoutes.tsx`: `/discovery-policies`, and `/discovery-rules` → `<Navigate to="/discovery-policies" replace />`;
  - `FE/components/AppShell.tsx` (the entry "Discovery policies", matching `/discovery-policies`) and `AppShell.test.tsx`;
  - `FE/stories/storyData.ts`: `DISCOVERY_POLICIES` holds `default`, and `sales-tables` with two rules, attached to the namespace `iceberg.sales`; `SCANNED_CATALOGS` is `iceberg`, with no failure;
  - `FE/stories/lakehouseHandlers.ts`.
- Test: the files above.

**Interfaces:**
- Consumes: the generated client of Tasks 5, 6 and 8: `useListTableDiscoveryPolicies`, `createTableDiscoveryPolicy`, `deleteTableDiscoveryPolicy`, `useListScannedCatalogs` and their query keys.
- Produces: `discoveryPoliciesPath()` (`"/discovery-policies"`), `discoveryPolicyPath(name)` and `discoveryPolicyVersionPath(name, version)`, each name `encodeURIComponent`-ed.

- [ ] **Step 1: Write the failing tests and stories.**
  - The list is a `ResourceListPage` (unframed):
    - The default comes first with a `Default` badge, then the rest by name.
    - The columns are Name (linking to the policy's page), Description, When no rule matches ("Manage" / "Do not manage"), Rules (a count, `tabular-nums`), Version and Attached to (a count).
    - Delete uses `ConfirmDeleteDialog`. It is disabled for the default ("The default policy cannot be deleted.") and for an attached policy ("Detach it from every target before deleting it.").
  - A scanned catalog with a current failure shows a negative `Banner` above the list: "Discovery cannot read catalog `<name>`: `<detail>`", or "Catalog `<name>` no longer exists" for `not_found`.
  - New policy opens `CreateDiscoveryPolicyDialog`:
    - It has Name, Description and When no rule matches, a `Select` preselected to "Do not manage".
    - A 409 or 422 shows the API's detail in the dialog.
    - On success it goes to the new policy's page.
  - Stories:
    - `Loaded`;
    - `OnlyDefault`;
    - `Error`;
    - `CannotAccess` (a failing catalog);
    - `Phone` (`globals: PHONE`, `expectNoHorizontalPageScroll`);
    - `OldRulesUrl` (`/discovery-rules` lands on the list).
- [ ] **Step 2: Run and watch them fail:** `<vitest> DiscoveryPoliciesPage CreateDiscoveryPolicyDialog AppShell`, then `<stories> DiscoveryPoliciesPage`. Expected: FAIL; the page does not exist.
- [ ] **Step 3: Implement** with design-system parts only.
- [ ] **Step 4: Run and watch them pass:** the same commands.
- [ ] **Step 5: Gate and commit.** `<gate> frontend`; commit `feat(console): list and create discovery policies (KCL-71)`.

### Task 11: Console: edit a discovery policy, and read a version and what it changed

**Files:**
- Create:
  - `FE/pages/DiscoveryPolicyPage.tsx` and `FE/pages/DiscoveryPolicyVersionPage.tsx`, each with `.stories.tsx` and `.test.tsx`;
  - `FE/components/DiscoveryRulesTable.tsx`, with `.stories.tsx` and `.test.tsx`;
  - `FE/lib/discoveryPolicyDraft.ts` and `FE/lib/discoveryPolicyChanges.ts`, each with `.test.ts`.
- Modify: `FE/components/DiscoveryRuleEditor.tsx`, with its story and test, for the new rule shape; `FE/AppRoutes.tsx` (two routes); `FE/stories/lakehouseHandlers.ts`.
- Test: the files above.

**Interfaces:**
- Consumes: `useGetTableDiscoveryPolicy`, `updateTableDiscoveryPolicy`, `useGetTableDiscoveryPolicyVersion` and their query keys, and `GlobListField` (unchanged).
- Produces:
  - `interface DiscoveryRuleDraft { key: string; id: string | null; outcome: "manage" | "unmanage"; namespaces: string[]; tableNames: string[] }`. An empty list means there is no condition on that attribute.
  - `interface DiscoveryPolicyDraft { version: number; description: string; noMatchOutcome: "manage" | "unmanage"; rules: DiscoveryRuleDraft[] }`.
  - The draft functions:
    - `draftFromPolicy(policy: TableDiscoveryPolicyApiResponse): DiscoveryPolicyDraft`;
    - `updateRequest(draft): UpdateTableDiscoveryPolicyApiRequest`, with the rules in draft order, a new rule without `id`, and only the non-empty conditions, `namespace` first, then `table_name`, with operator `glob`;
    - `newRuleDraft(key: string): DiscoveryRuleDraft`, with outcome `manage` and no globs;
    - `movedRule(rules, key, by: -1 | 1)`;
    - `ruleHasCondition(rule): boolean`.
  - `DiscoveryRulesTable({ rules, readOnly, actions?, hints? })`:
    - It is a `DataTable` with columns `#` (the position), Outcome (a neutral `Badge`), Namespace and Table name (the globs in `font-mono`, `—` when none).
    - Unless `readOnly`, it adds Move up, Move down, Edit and Delete.
    - Its caption is "Discovery rules, read top to bottom".
    - `hints?: Record<string, string[]>` lists text under a rule's conditions, keyed by rule `key`.
  - `discoveryPolicyChanges(previous: TableDiscoveryPolicyVersionApiResponse, current: TableDiscoveryPolicyVersionApiResponse): DiffListItem[]` returns:
    - one item per rule id: `added`, `removed` or `changed`, where changed means the outcome or a condition changed, with `before` and `after` as the rule's one-line text;
    - a `changed` item `Moved from #i to #j` for a rule kept with the same content at a new position;
    - an item for the no-match outcome and one for the description when they changed.

- [ ] **Step 1: Write the failing tests and stories.**
  - `discoveryPolicyDraft.test.ts`:
    - a policy goes draft → request unchanged;
    - a new rule is sent without `id`;
    - a rule with only table-name globs sends one `table_name` condition.
  - `discoveryPolicyChanges.test.ts`:
    - a rule added and a rule removed;
    - an outcome flipped reads `changed`, with before "Manage" and after "Do not manage";
    - two rules swapped read as two moves;
    - identical versions give no item that is not `unchanged`.
  - `DiscoveryRuleEditor`:
    - it has an Outcome select, Namespace globs and Table name globs;
    - with both empty, Save is refused and the dialog says "A rule needs at least one condition: a namespace or a table name glob.";
    - keyboard: the Tab order, and Escape closes and returns focus.
  - `DiscoveryPolicyPage`:
    - The header shows the name and "Version N, saved `<time>`", with links `vN` … `v1` to the version pages (newest first, the newest 10 shown and the rest behind "Show N earlier versions").
    - It has a description `TextArea`, a "When no rule matches" `Select`, and the rules table with Add rule.
    - Save and Discard are enabled only when the draft differs.
    - A 409 shows "Someone else changed this policy. Reload to see their version." with Reload, and a 422 shows the detail.
    - After a save it shows "Saved. Discovering tables…".
    - Deleting a rule of the draft needs no confirmation.
    - The default shows an information `Banner` with its fixed description and a read-only rules table, and no Save.
  - `DiscoveryPolicyVersionPage`:
    - It shows the description, the no-match outcome and `DiscoveryRulesTable readOnly`.
    - It has a "Changes from v`N-1`" `DiffList`; v1 reads "First version".
    - A non-numeric version shows "a version is a whole number", and a 404 shows the API's detail.
    - The breadcrumbs are Discovery policies → name → `name vN`.
  - Stories for both pages:
    - `Loaded`;
    - `Default`;
    - `Conflict` (the edit page);
    - `Error`;
    - `Phone`;
    - the version page's `Changes` story asserts one added and one removed row.
- [ ] **Step 2: Run and watch them fail:** `<vitest> discoveryPolicyDraft discoveryPolicyChanges DiscoveryRuleEditor DiscoveryRulesTable DiscoveryPolicyPage DiscoveryPolicyVersionPage`. Expected: FAIL.
- [ ] **Step 3: Implement.** Keep the draft-against-version pattern of today's `DiscoveryRulesPage`: a refetch never moves the draft's version, and the refetch happens in `onSettled`.
- [ ] **Step 4: Run and watch them pass:** the same command and `<stories> DiscoveryPolicy`.
- [ ] **Step 5: Gate and commit.** `<gate> frontend`; commit `feat(console): edit a discovery policy and read what each version changed (KCL-71)`.

### Task 12: Console: attach and detach on the policy page, with hints and each catalog's scan state

**Files:**
- Create: `FE/components/DiscoveryPolicyAttachments.tsx` and `FE/components/AttachDiscoveryPolicyDialog.tsx`, each with `.stories.tsx` and `.test.tsx`; `FE/lib/discoveryRuleHints.ts`, with `.test.ts`.
- Modify: `FE/pages/DiscoveryPolicyPage.tsx` (an "Attached to" section under the rules, and the hints passed to the rules table); `FE/stories/lakehouseHandlers.ts`.
- Test: the files above.

**Interfaces:**
- Consumes: `useListTableDiscoveryPolicyAttachments`, `attachTableDiscoveryPolicy`, `detachTableDiscoveryPolicy`, `useListScannedCatalogs`, `useListCatalogs` (the catalog context), and `targetPagePath` / `targetName` from `FE/lib/policyPaths.ts`.
- Produces:
  - `ruleHints(rule: DiscoveryRuleDraft, attachments: { type: string; path: string[] }[]): string[]` returns the two hints of Global Constraints, each at most once per rule:
    - the table hint when any attachment is a table and the rule has a condition;
    - the namespace hint, naming the first namespace attachment, when the rule has namespace globs.
  - `DiscoveryPolicyAttachments({ policyName })` lists each attachment:
    - its kind, its linked name, and a neutral `Orphaned` badge when the target left the catalog;
    - its catalog's scan state: "Scanned `<relative time>`", "Not scanned yet", "Not scanned: no policy in `<catalog>` manages tables", or a negative "Cannot access" / "Catalog not found" with the detail;
    - a Detach button, `aria-label="Detach from <name>"`, with no confirmation (the house rule for detach).

- [ ] **Step 1: Write the failing tests and stories.**
  - The empty state reads "Not attached. Attach it to a catalog, namespace or table to apply it."
  - Attach opens the dialog:
    - Type: Catalog, Namespace or Table;
    - Catalog, a `Select` from `GET /v1/catalogs`;
    - Namespace, a dot-joined `TextField` hidden for a catalog;
    - Table, a `TextField` shown only for a table.
    - The API's 403 or 404 detail shows inside the dialog and keeps it open.
  - After an attach or a detach, success or not, the page refetches this policy's attachments, the policy list and `/v1/scanned-catalogs`.
  - There is a keyboard test for the dialog.
  - `discoveryRuleHints.test.ts` covers both hints and the case with none.
  - The scan-state line is tested for all five states.
  - Stories: `Attached` (three kinds), `AttachDialog`, `CannotAccess` and `Phone`.
- [ ] **Step 2: Run and watch them fail:** `<vitest> DiscoveryPolicyAttachments AttachDiscoveryPolicyDialog discoveryRuleHints DiscoveryPolicyPage`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass:** the same command and `<stories> DiscoveryPolicy`.
- [ ] **Step 5: Gate and commit.** `<gate> frontend`; commit `feat(console): attach and detach discovery policies from the policy page (KCL-71)`.

### Task 13: Console: the table page reads the scanned catalogs, and the rules page goes

**Files:**
- Delete: `FE/pages/DiscoveryRulesPage.tsx` with its stories and test; `FE/lib/discoveryRuleDraft.ts`.
- Modify:
  - `FE/pages/TablePage.tsx` (`useListScannedCatalogs` instead of `useListCoveredCatalogs`) and `FE/lib/tableMaintenanceState.ts`;
  - `FE/components/MaintenanceEmptyState.tsx`, with its test;
  - `FE/components/tabs/OverviewTab.tsx`;
  - `FE/stories/{lakehouseHandlers,storyData}.ts`;
  - every page test that stubs `/v1/discovery-rules*`: `TablePage.test.tsx`, `TablePage.mobile.test.tsx` and `TableListPage.test.tsx`;
  - `FE/pages/TablePage.stories.tsx`.
- Test: the files above.

**Interfaces:**
- Consumes: `useListScannedCatalogs`, `useListTableDiscoveryPolicies` and `useGetTableDiscoveryPolicyVersion`.
- Produces:
  - `tableMaintenanceState(catalog, scanned: QueryResult<ScannedCatalogApiResponse[]>, maintenance)` works in this order:
    1. a catalog that is not scanned is `catalog-not-scanned`;
    2. a scanned catalog with a current `cannot_access` failure is `catalog-cannot-access`;
    3. then the record checks of today.
  - `MaintenanceEmptyReason = "catalog-not-scanned" | "catalog-cannot-access" | "not-found" | "unmanaged" | "dropped"`. The messages:
    - `catalog-not-scanned`: "no discovery policy in this catalog manages tables";
    - `catalog-cannot-access`: "discovery cannot read this catalog with the platform's catalog credential";
    - `unmanaged`: "the discovery policy that applies does not manage this table".
    - `not-found`, `unmanaged`, `catalog-not-scanned` and `catalog-cannot-access` link to "Discovery policies" (`/discovery-policies`).
  - The Overview's Table panel, for a managed table, shows: "Maintenance: managed · discovery policy `<name>` v`<N>`", linking to `discoveryPolicyVersionPath`, then " · rule `<position>`" or " · no rule matched".
    - A policy missing from the list shows `matched_policy_id` in `font-mono`, with no link and no rule position.

- [ ] **Step 1: Write the failing tests.**
  - A table in an unscanned catalog shows the not-scanned reason with the link.
  - A failing catalog shows the cannot-access reason.
  - The Overview names `sales-tables v2 · rule 1` for a table its first rule decided.
  - No request goes to `/v1/discovery-rules*` from any page; assert it on the MSW call log in `TablePage.test.tsx`.
  - The `TablePage` stories `NotScanned` and `CannotAccess`, and the rule link story, now name the policy.
- [ ] **Step 2: Run and watch them fail:** `<vitest> TablePage MaintenanceEmptyState OverviewTab tableMaintenanceState`. Expected: FAIL.
- [ ] **Step 3: Implement.** Afterwards `grep -rn "discovery-rules\|DiscoveryRules\|useListCoveredCatalogs\|catalog-not-covered" src/data-platform/frontend/src --include='*.ts*' | grep -v api/generated` prints only the redirect route.
- [ ] **Step 4: Run and watch them pass:** `<vitest>` and `<stories>`.
- [ ] **Step 5: Gate and commit.** `<gate> frontend`; commit `feat(console): say why a table is not managed in terms of discovery policies (KCL-71)`.

### Task 14: Remove the discovery rules and the configured catalog list

**Files:**
- Delete:
  - `TM/application/domain/model/table_discovery_rules/`, `TM/application/port/inbound/table_discovery_rules/`, `TM/application/port/outbound/table_discovery_rules/`, `TM/application/service/table_discovery_rules/`, `TM/adapter/outbound/table_discovery_rules/` and `TM/adapter/inbound/web/table_discovery_rules/`;
  - `tests/context/table_maintenance/fakes/in_memory_table_discovery_rules_repo.py`, and every test directory named `table_discovery_rules`.
- Modify:
  - `TM/adapter/outbound/shared/sql/create_schema.py`: `AGGREGATE_SQL_PACKAGES` drops the rules package;
  - `TM/adapter/inbound/web/{register_routes.py,shared/web_use_cases.py}`;
  - `translate_domain_errors.py`, which drops `StaleDiscoveryRulesVersion`;
  - `tests/architecture/{test_aggregates,test_service_structure}.py`;
  - `bootstrap/configs/catalog_settings.py`, which drops `names`, and the `app_settings.py` docstring example;
  - `bootstrap/container/{use_cases,repositories,build_use_cases,build_repositories,build_connected_use_cases,build_web_use_cases}.py`;
  - the `tests/bootstrap/**` tests that name rules or `catalog.names`;
  - `tests/.../adapter/inbound/web/policy_web_world.py`;
  - `platform/25-lakehouse-control-plane/chart/values.yaml` (drops `catalog.names`), `chart/templates/configmap.yaml` (drops `GLAC_CATALOG__NAMES`) and `validate.sh`;
  - `openapi.json` and the client; the `discovery-rules` module disappears.
- Test: `tests/architecture`, `tests/bootstrap` and the whole backend suite.

**Interfaces:**
- Consumes: Tasks 7, 9 and 13. Nothing reads the rules any more, and the console no longer imports the `discovery-rules` client.
- `validate.sh` after this task:
  - The `GLAC_CATALOG__NAMES` block goes.
  - `api_get /v1/discovery-policies/default` must answer `"is_default":true` with `"rules":[]`.
  - `/v1/discovery-rules` joins the `old_route` 404 loop.
  - The `table-discovery:catalog=` schedules listed by `temporal schedule list` in `deployment/temporal-admintools` must be exactly the catalogs of `GET /v1/scanned-catalogs`, none missing and none extra.

- [ ] **Step 1: Write the failing tests:** `test_discovery_rules_routes_are_gone(client)`, where `GET /v1/discovery-rules` and `GET /v1/discovery-rules/catalogs` answer 404, and `test_catalog_settings_have_no_names()`, where `"names" not in CatalogSettings.model_fields`.
- [ ] **Step 2: Run and watch them fail:** `<pytest> tests -k "discovery_rules_routes_are_gone or catalog_settings_have_no_names" -v`. Expected: FAIL; both still exist.
- [ ] **Step 3: Delete and rewire.** `grep -rn "discovery_rules\|DiscoveryRules\|ListCoveredCatalogs\|catalog\.names\|rules_version\|GLOBAL_TABLE_DISCOVERY_RULES_ID" src/data-platform/backend --include='*.py'` prints nothing. Then `<generate>`. `helm template /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/chart | grep -c GLAC_CATALOG__NAMES` prints `0`, and `bash -n` passes on `validate.sh`.
- [ ] **Step 4: Run and watch them pass:** `<pytest> -q` and `uv run --project /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend --directory /Users/kcl/Projects/retail-lakehouse/src/data-platform/backend lint-imports`.
- [ ] **Step 5: Gate and commit.** `<gate> all`; commit `refactor(table-maintenance): remove the discovery rules list and the configured catalog names (KCL-71)`.

### Task 15: e2e script and documentation

**Files:**
- Modify:
  - `platform/25-lakehouse-control-plane/e2e.sh` and `README.md`;
  - the root `CLAUDE.md`, `src/data-platform/backend/CLAUDE.md` and `src/data-platform/frontend/CLAUDE.md`;
  - `docs/adr/0005-bounded-contexts-and-context-map.md`, `docs/adr/0011-prefixed-resource-ids.md` and `docs/adr/0012-policies-on-the-catalog-hierarchy.md`;
  - `docs/polaris/troubleshooting-catalog-reset.md`, if it still names `GLAC_CATALOG__NAMES`;
  - `docs/agents/known-follow-ups.md` and `docs/agents/project-history.md`.

- [ ] **Step 1: e2e.** Read `e2e.sh` at HEAD first. "Ensuring the discovery rule" becomes:
  - When `GET /v1/discovery-policies/tm-e2e` is 404, create `tm-e2e`: no-match `unmanage`, and one rule `manage` on `{"attribute": "table_name", "operator": "glob", "values": ["tm_e2e_*"]}`.
  - After the `CREATE SCHEMA` / `CREATE TABLE` statement, `PUT …/tm-e2e/attachments` with `{"target": {"type": "namespace", "path": ["iceberg", "${SCHEMA}"]}}`.
  - `RULE_ID` is the policy's `rules[0].id`.
  - Wait until `temporal schedule describe --schedule-id table-discovery:catalog=iceberg` succeeds. `GET /v1/scanned-catalogs` must list `iceberg` with `failure: null`.
  - `assert_prefixed_ids` also checks the policy's `dp-` id and the attachment's `da-` id.
  - The e2e never detaches **(decided: detaching would unmanage the e2e tables in the middle of the suite)**. The detach checks are in Task 16.
  - Run `uv run --directory /Users/kcl/Projects/retail-lakehouse pre-commit run shellcheck --all-files`.
- [ ] **Step 2: Docs.**
  - README:
    - The settings paragraph: there are no catalog names, and the scanned catalogs follow the attachments.
    - The API table: the `discovery-policies` rows and `/scanned-catalogs` replace the discovery-rules row.
    - The curl example: create a policy, then attach it.
    - The workflow-id table: `trigger=policy-changed:change={id}` beside `trigger=adhoc`. A schedule exists only while its catalog is scanned, and the worker syncs the schedules at start.
  - The root `CLAUDE.md` Project Vision lists `TableDiscoveryPolicy` and `TableDiscoveryPolicyAttachment` instead of `TableDiscoveryRules`.
  - Backend `CLAUDE.md`:
    - the aggregate list;
    - the DTO example becomes `UpdateTableDiscoveryPolicyApiRequest` / `TableDiscoveryPolicyApiResponse` in `adapter/inbound/web/table_discovery_policy/dto.py`;
    - one paragraph on discovery: the nearest attachment, `discovered_by`, the derived scanned catalogs, the schedule sync and the rescan after a change, the recorded scan failures, and `PolicyTarget` in `shared`.
  - Frontend `CLAUDE.md`:
    - the `MaintenanceEmptyState` reasons;
    - the Overview's discovery line;
    - the three discovery policy pages;
    - attach living on the policy page until KCL-98;
    - "Draft-only deletes" naming a discovery rule of a policy draft.
  - ADR 0005: one "Updated 2026-11-21" line on the aggregate list.
  - ADR 0011: the rows `dp-` TableDiscoveryPolicyId and `da-` TableDiscoveryPolicyAttachmentId; the default discovery policy has the fixed id.
  - ADR 0012, a "2026-11-21 note (KCL-71)":
    - the condition shape `{attribute, operator, values}`;
    - outcomes `manage` / `unmanage`;
    - attach as `PUT …/attachments` and detach as `DELETE …/attachments/{attachment_id}`, the shape KCL-98 gives maintenance;
    - the "a target must exist" check, which allows an empty catalog or namespace.
  - `known-follow-ups.md`:
    - Remove the entry "Catalog context: maintenance covers only the catalogs in … `catalog.names`".
    - From the KCL-73 entry, remove the sentence on `"id": ""` and the one on the hand-copied name pattern.
    - Add, each tagged 2026-11-21 and KCL-71:
      - two concurrent changes can sync the schedules in the wrong order until the next change or worker start;
      - a schedule sync or rescan that fails after a change is only logged;
      - a renamed table's recorded match can name a policy that no longer applies until the next scan;
      - "What each version changed" is worked out in the console only; there is no API for it.
  - `project-history.md`, one KCL-71 line dated the day it lands. It names:
    - versioned discovery policies (`dp-`, the default `dp-0…0` manages nothing and cannot change);
    - attachments (`da-`, nearest wins, detach by id);
    - the derived scanned catalogs, their schedules and the rescan after a change;
    - "cannot access" recorded and shown;
    - `GLAC_CATALOG__NAMES` gone;
    - the console pages `/discovery-policies`.

    It ends with "No migration: rebuild the cluster."
- [ ] **Step 3: Gate and commit.** `<gate> all`; commit `docs(table-maintenance): describe discovery policies and drive the e2e through them (KCL-71)`.

### Task 16: KCL-71 checks for the batched cluster verification (controller)

The controller runs these in the one rebuild batched with KCL-94, KCL-95 and KCL-98; this task does no rebuild of its own. The batch's rebuild comes first: `task -d /Users/kcl/Projects/retail-lakehouse offboard KUBE_CONTEXT=retail-lakehouse`, then `onboard KUBE_CONTEXT=retail-lakehouse`, then `apps:validate KUBE_CONTEXT=retail-lakehouse`, which exits 0 with no discovery schedule and `GET /v1/scanned-catalogs` = `{"catalogs": []}` before any attach. API calls go through the e2e script's `api` helper or the console, and Temporal through `deployment/temporal-admintools` (`kubectl exec deployment/temporal-admintools --namespace temporal --context retail-lakehouse -- temporal …`).

- [ ] **Check 1: The default.** `GET /v1/discovery-policies/default` is `is_default: true`, with no rules and `unmanage`. `PUT` and `DELETE` on it answer 409.
- [ ] **Check 2: Attach creates the schedule.**
  - Create a policy that manages `table_name ["*"]`, with no-match `unmanage`, and attach it to a namespace of `iceberg` that holds tables.
  - Within a minute:
    - `temporal schedule describe --schedule-id table-discovery:catalog=iceberg` succeeds;
    - a `trigger=policy-changed` run completes;
    - `GET /v1/tables?status=managed` lists that namespace's tables, each with `matched_policy_id`, `matched_policy_version` and `matched_rule_id` set.
- [ ] **Check 3: The nearest wins.** Attach `default` to one of those tables. After its rescan that table is unmanaged, and the others stay managed.
- [ ] **Check 4: Detach deletes the schedule.** Detach the namespace policy by its `da-` id.
  - Every table of the namespace becomes unmanaged, and each table's reconciliation workflow received `stopped`.
  - `temporal schedule list` shows no `table-discovery:` schedule, and `GET /v1/scanned-catalogs` is empty.
- [ ] **Check 5: Empty and missing targets.** Create an empty namespace through the catalog API and attach a policy to it: 200. Attach to a made-up namespace: 404, with nothing stored.
- [ ] **Check 6: Cannot access.** Create a second catalog through Polaris's management API and give the platform principal's catalog role no grant on it, or revoke its read grants there. Then:
  - attaching there answers 403 with the detail;
  - after granting, attaching, and revoking again, the next scheduled scan records `cannot_access`. `GET /v1/scanned-catalogs` shows it, the console's list page shows the banner, and a table page in that catalog shows "discovery cannot read this catalog …".
  - Restore the grant afterwards.
- [ ] **Check 7: Worker start.** Delete the `iceberg` schedule by hand while a managing policy is attached, then `kubectl rollout restart deployment/table-maintenance-worker --namespace lakehouse-control-plane --context retail-lakehouse`. The schedule is back once the new pod is ready.
- [ ] **Check 8: Console, at 1280px and at 390px.**
  - The sidebar shows Discovery policies.
  - Create a policy, add and reorder rules, and save: version 2 appears, v1 is readable, and v2's page lists what changed.
  - Attach and detach from the page; each row shows its scan state.
  - The default is read-only.
  - `/discovery-rules` redirects.
  - A table in an unscanned catalog shows "no discovery policy in this catalog manages tables".
  - The Overview names the policy, version and rule.
  - At 390px there is no horizontal scroll.
- [ ] **Check 9: e2e.** When Trino runs (it is paused since 2026-11-19, `platform/CLAUDE.md`), `KUBE_CONTEXT=retail-lakehouse bash /Users/kcl/Projects/retail-lakehouse/platform/25-lakehouse-control-plane/e2e.sh` passes. Otherwise say so in the report. Then run `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`, and record the results on KCL-71 in a dated comment.
