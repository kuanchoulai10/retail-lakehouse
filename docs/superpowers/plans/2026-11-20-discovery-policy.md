# Discovery Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the one platform-wide discovery rule list with named, versioned discovery policies attached to catalogs, namespaces and tables, where the nearest attachment decides whether a table is managed and the catalogs that get scanned follow from the attachments.

**Architecture:** Two new aggregates in `table_maintenance`: `TableDiscoveryPolicy` (name, `dp-` id, kept versions, content = ordered rules plus a no-match outcome) and `TableDiscoveryPolicyAttachment` (`da-` id, one per target). `PolicyTarget` and the nearest-attachment walk move to the context's `shared` model so maintenance and discovery resolve the same way (ADR 0012). Every scan resolves each table's nearest discovery attachment; every policy change re-derives the scanned catalogs, syncs one Temporal schedule per scanned catalog and rescans the affected ones. `TableDiscoveryRules`, `/v1/discovery-rules*` and `GLAC_CATALOG__NAMES` go.

**Tech Stack:** Python 3.14, Pydantic, SQLAlchemy Core, FastAPI, Temporal Python SDK (schedules), PyIceberg, Helm, React + TanStack Query + orval, MSW, Storybook/vitest.

**Spec:** Linear KCL-71 (https://linear.app/kcl10/issue/KCL-71), read with its comments: the scope change of 2026-11-19 15:05 governs and voids the description where they conflict (one platform-wide policy, priority/enabled rules, catalog/namespace/table globs, the interval and the catalog list in the policy, migrating the rules). `docs/adr/0012-policies-on-the-catalog-hierarchy.md` ("Discovery policy", "Aggregates and API") is the model. KCL-98 owns `effective-policies`, the per-target policy panel and the maintenance `mappings` → `attachments` rename; KCL-93 runs before this plan.

## Global Constraints

Decisions are marked **(decided)** with the reason; everything else is copied from the spec.

- **KCL-93 lands first.** Compaction rounds, candidates, the admission workflow, `/v1/compaction-rounds*`, `/v1/scheduler-settings`, `/v1/tables/{uuid}/compaction-candidates`, the console Compaction rounds page and Candidates tab are gone, and `/v1/platform-settings` no longer lives under `compaction_round`. No task touches them; where a file list below names a test that KCL-93 deleted, skip it. `apply_worker_startup` here means its post-KCL-93 body (search attributes check plus the discovery schedules).
- **Resolution (ADR 0012).** For a table, walk: table attachment (by Iceberg uuid), then namespace attachments deepest first, then the catalog attachment, then the platform default. The nearest replaces its parents whole; nothing merges. An attachment always means its policy's latest version.
- **Default discovery policy.** id `dp-00000000000000000000000000`, name `default`, no rules, `no_match_outcome` `unmanage`, description `Manages nothing. Attach another discovery policy to a catalog, namespace or table to manage its tables.` It cannot be updated or deleted (409). **(decided)** It may be attached anywhere: attaching it to a namespace or table under a managing catalog is how a user opts that part out, which ADR 0012's "replaces its parents whole" already implies.
- **Content wire shape (decided, modelled on Kubernetes `matchExpressions` `{key, operator, values}` so labels and properties add attributes and operators without a new structure):**
  ```json
  {"description": "", "no_match_outcome": "unmanage",
   "rules": [{"id": "dr-…", "outcome": "manage",
              "conditions": [{"attribute": "namespace", "operator": "glob", "values": ["sales", "sales.*"]},
                             {"attribute": "table", "operator": "glob", "values": ["orders_*"]}]}]}
  ```
  Outcomes are exactly `manage` and `unmanage` **(decided: the words of `Table.manage()` / `unmanage()` and the `managed` / `unmanaged` statuses)**. Attributes are exactly `namespace` and `table`; the only operator is `glob`.
- **Rules.** Read top to bottom; the first rule whose conditions all hold decides; none → `no_match_outcome`. A rule has at least one condition (ADR). **(decided)** An attribute appears at most once per rule (two `namespace` conditions that must both hold are a confusing way to write one), `values` is non-empty and holds no empty string. Glob semantics are today's: `fnmatchcase`, case-sensitive, a namespace glob matches the dot-joined namespace (`*` crosses dots). **(decided)** Rules have no `priority` and no `enabled`: list order is the order (ADR "ordered rules"), and a kept version history makes "remove the rule" safe where `enabled` used to be the undo.
- **Rule ids.** `dr-` (kept). The server mints an id for every rule sent without one; on update a rule may carry only an id of the policy's current version, anything else is 422 `unknown discovery rule id dr-…` (the guard of today's `replace`). `Table.matched_rule_id` points at the deciding rule; **(decided)** it is `None` for a table managed by the no-match outcome, because no rule decided it.
- **Names.** 1 to 64 of `[A-Za-z0-9_-]`, never shaped like a prefixed id, unique per kind (a discovery and a maintenance policy may share a name, ADR 0012). **(decided)** One shared checker `checked_policy_name` serves both name value objects.
- **Attachments.** id prefix `da-` **(decided: "discovery attachment"; `pa-` stays the maintenance attachment's; ADR 0011's list gets the row)**. One attachment per target, by `PolicyTarget.key()`, as a unique index. **(decided)** The SQL row also stores the target's catalog in an indexed `catalog` column, so a scan loads only its catalog's attachments.
- **Targets must exist when attached** (as maintenance does today): a table is resolved to its uuid through the catalog, a catalog or namespace must hold a table. **(decided)** A catalog the platform's Polaris credential may not read is refused with 403 and the detail `the platform's catalog credential cannot read catalog <name>` (new `CatalogAccessDeniedError` from the table-reading gateway). The console's attach dialog picks the catalog from `GET /v1/catalogs` (the issue's "pick from Polaris's catalogs").
- **Scanned catalogs are derived.** A catalog is scanned when some discovery attachment in it (catalog, namespace or table target) points at a policy that can resolve to manage (a `manage` rule or `no_match_outcome` `manage`). Each scanned catalog has the Temporal schedule `table-discovery:catalog={catalog}` (id unchanged) firing every `GLAC_DISCOVERY_INTERVAL_SECONDS`; no other `table-discovery:catalog=` schedule exists.
- **Scan interval stays a platform setting** (`GLAC_DISCOVERY_INTERVAL_SECONDS`, chart `worker.discoveryIntervalSeconds`, default 600). **(decided)** It is now bounded `ge=60, le=86400`, the floor the issue asked for so Polaris and the database are not scanned in a loop.
- **`GLAC_CATALOG__NAMES` and chart `catalog.names` are removed (decided):** nothing else reads them (checked: only discovery, `ListCoveredCatalogs` and the old replace service).
- **After a change (decided).** Update, attach and detach each: compute the scanned catalogs before and after the change; sync the schedules to the "after" set (create missing, rewrite interval and unpause existing, delete extra); start one ad hoc catalog-wide scan for every affected catalog (the policy's attachment catalogs for an update, the target's catalog for attach and detach) that is scanned before or after. A catalog that stops being scanned therefore gets one last scan, in which every table resolves to the default and becomes unmanaged (the issue's open question "what happens to its tables": unmanaged), and then has no schedule. Both steps are best effort after the commit (logged, never fail the request); the worker re-syncs the schedules at every start. Create and delete do neither: an unattached policy affects no table, and delete is refused while attached.
- **Ad hoc scan ids.** `SendDiscoveryRequestGatewayInput.rules_version` becomes `change_id: str | None`; a change's scan is `table-discovery:catalog={catalog}:trigger=policy-changed:change={change_id}` with a fresh 32-hex `uuid4` per change, so a change never joins a run that read older policies (today's guarantee per rules version).
- **API (ADR 0012):** `GET, POST /v1/discovery-policies`; `GET, PUT, DELETE /v1/discovery-policies/{name}`; `GET /v1/discovery-policies/{name}/versions/{version}`; `GET, PUT, DELETE /v1/discovery-policies/{name}/attachments` (bodies as the maintenance `mappings` today: `{"target": {"type", "path"}}`, detach may add `table_uuid`). **(decided)** `GET /v1/scanned-catalogs` → `{"catalogs": [...]}` replaces `GET /v1/discovery-rules/catalogs`; it is top level so it can never collide with a policy named `scanned-catalogs`. Errors: 404 unknown policy or target, 409 taken name / stale version / default changed or deleted / delete while attached, 422 invalid content or unknown rule id, 403 unreadable catalog. All routes carry the OpenAPI tag `discovery-policies`.
- **Not in this plan:** `effective-policies`, the per-target policy panel on catalog/namespace/table pages, renaming maintenance `mappings`, `applicable-policy` (all KCL-98); maintenance policy content (KCL-91).
- **Console (decided).** Routes `/discovery-policies` (list), `/discovery-policies/:name` (edit page: rules are a page-level draft with Save / Discard, as the rules page is today, too much for a dialog), `/discovery-policies/:name/versions/:version` (read-only); `/discovery-rules` redirects to `/discovery-policies`; the sidebar entry reads "Discovery policies". Attach and detach live on the policy page until KCL-98 adds them to target pages. Outcomes read "Manage" / "Do not manage". The "condition without effect" hint is console-only (ADR: allowed, the console hints).
- **No data migration.** Old rules are not converted; the cluster is rebuilt (`task offboard`, then `task onboard KUBE_CONTEXT=retail-lakehouse`). Code stops creating `table_discovery_rules` and `table_discovery_rule_items`; it never drops them.
- Follow `CLAUDE.md`: one object per file, `from __future__ import annotations`, StrEnum, ABC ports, TDD, `uv run`, never `cd`, kubectl verb first, never two test suites at once, explicit paths in `git add`, never `--no-verify`. Every commit passes `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend` (or `scope=frontend`, or `scope=all` when both sides change); a backend API change regenerates the client with `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api` and commits it with the backend change.
- Commit messages end with `Claude-Session: https://claude.ai/code/session_01PccGCvSoNC4d9wg6ucpuHW`.

## Review Focus

- A table attached by uuid that is renamed or moved to another namespace keeps its table-level policy; the namespace part of its walk uses the new name (Task 7).
- A table carrying the default policy (or any `unmanage` policy) on itself under a catalog whose policy manages everything stays unmanaged: the nearest wins over a parent that says manage (Tasks 3 and 7).
- Detaching the last managing policy from a catalog unmanages the catalog's managed tables in one final scan and deletes its schedule; a Temporal failure while doing so still answers 204 and logs (Task 8).
- An update naming a rule id from another policy, a misshapen id or a stale version is refused with nothing saved and no scan started (Task 5).
- A catalog event for a table in a catalog nobody scans registers it unmanaged and starts no workflow, instead of failing the hint (Task 7).

---

## File Structure

Backend paths are relative to `src/data-platform/backend/`; `TM` = `context/table_maintenance`, tests mirror under `tests/context/table_maintenance/`. Frontend paths are relative to `src/data-platform/frontend/src/`.

| File | Responsibility |
|---|---|
| `TM/application/domain/model/shared/policy_target.py`, `policy_target_type.py`, `checked_policy_name.py` | target value object and type (moved), shared name rule |
| `TM/application/domain/service/shared/candidate_policy_targets.py`, `enclosing_policy_targets.py`, `nearest_attached.py` | the walk up the hierarchy (moved) and the nearest-attachment pick |
| `TM/application/service/shared/policy_target_from_request.py`, `scope_target_in_listing.py`, `target_in_catalog.py` | request → target, existence and orphan checks (moved/extracted) |
| `TM/adapter/inbound/web/shared/dto.py` | `PolicyTargetApiRequest`, `DetachPolicyTargetApiRequest`, `PolicyTargetApiResponse` (moved) |
| `TM/application/domain/model/table_discovery_policy/` (new) | aggregate, content, rule, condition, decision, ids, name, exceptions |
| `TM/application/domain/model/table_discovery_policy_attachment/` (new) | attachment aggregate and id |
| `TM/application/domain/service/table_discovery_policy_attachment/` (new) | `decide_table_discovery`, `scanned_catalogs` |
| `TM/application/port/outbound/table_discovery_policy/`, `…/table_discovery_policy_attachment/` (new) | repos, `SyncScannedCatalogsGateway` |
| `TM/application/port/inbound/table_discovery_policy/`, `…/table_discovery_policy_attachment/` (new) | use case ports |
| `TM/application/service/table_discovery_policy/`, `…/table_discovery_policy_attachment/` (new) | services, `apply_discovery_change` |
| `TM/application/service/table/discovery_decider.py` (new), `sync_discovered_tables.py`, `register_discovered_table.py`, `apply_discovery_to_known_table.py`, `process_table_hint.py`, `TM/application/domain/service/table/decide_table_management.py`, `TM/application/domain/model/table/table.py` | scans decide by policy |
| `TM/adapter/outbound/table_discovery_policy/sql/`, `…/table_discovery_policy_attachment/sql/` (new) | SQL tables, mappers, repos |
| `TM/adapter/inbound/web/table_discovery_policy/`, `…/table_discovery_policy_attachment/` (new) | routers, DTOs |
| `TM/adapter/hybrid/temporal/outbound/table_discovery_policy_attachment/` (new) | `SyncScannedCatalogsTemporalGateway`, `catalog_scan_schedule` |
| `TM/adapter/outbound/table/pyiceberg/read_table_metadata_pyiceberg_gateway.py`, `TM/application/port/outbound/table/read_table_metadata/catalog_access_denied_error.py` (new) | 403 for an unreadable catalog |
| `bootstrap/configs/app_settings.py`, `catalog_settings.py`, `bootstrap/container/*`, `bootstrap/worker.py` | wiring, startup sync, settings |
| removed: `TM/**/table_discovery_rules/`, `TM/adapter/hybrid/temporal/inbound/ensure_table_discovery_schedule.py`, `ListCoveredCatalogs*` | the old aggregate |
| `pages/DiscoveryPoliciesPage.tsx`, `DiscoveryPolicyPage.tsx`, `DiscoveryPolicyVersionPage.tsx` (new) | console pages |
| `components/DiscoveryRulesTable.tsx`, `DiscoveryRuleEditor.tsx`, `CreateDiscoveryPolicyDialog.tsx`, `DiscoveryPolicyAttachments.tsx`, `AttachDiscoveryPolicyDialog.tsx` | console components |
| `lib/discoveryPolicyDraft.ts`, `discoveryPolicyPaths.ts`, `discoveryRuleHints.ts` | console logic |
| `platform/25-lakehouse-control-plane/chart/values.yaml`, `templates/configmap.yaml`, `validate.sh`, `e2e.sh`, `README.md` | platform |

---

### Task 1: Move the policy target and its walk to `shared`

Pure refactor: behaviour, routes and OpenAPI unchanged.

**Files:**
- Move: `TM/application/domain/model/table_maintenance_policy_attachment/policy_target.py`, `policy_target_type.py` → `TM/application/domain/model/shared/`; `TM/application/domain/service/table_maintenance_policy_attachment/{candidate_policy_targets,enclosing_policy_targets}.py` → `TM/application/domain/service/shared/` (delete the emptied domain-service package); `TM/application/service/table_maintenance_policy_attachment/{policy_target_from_request,scope_target_in_listing}.py` → `TM/application/service/shared/`; `PolicyTargetKind`, `PolicyTargetApiRequest`, `DetachPolicyTargetApiRequest`, `PolicyTargetApiResponse` → `TM/adapter/inbound/web/shared/dto.py`
- Create: `TM/application/domain/model/shared/checked_policy_name.py`, `TM/application/domain/service/shared/nearest_attached.py`, `TM/application/service/shared/target_in_catalog.py`
- Modify: every importer (`grep -rn "PolicyTarget\|candidate_policy_targets\|enclosing_policy_targets\|policy_target_from_request\|scope_target_in_listing"`), `table_maintenance_policy_name.py` (calls the checker), `resolve_applicable_table_maintenance_policy.py` and `notify_policy_change.py` (use `nearest_attached`), `list_table_maintenance_policy_attachments.py` (uses `target_in_catalog`); `PolicyTargetType`'s docstring says "a policy", not "a maintenance policy"
- Test: move the tests of the moved modules to the mirrored `shared` paths; new `tests/…/domain/service/shared/test_nearest_attached.py`, `tests/…/domain/model/shared/test_checked_policy_name.py`

**Interfaces:**
- Produces: `PolicyTarget`, `PolicyTargetType` from `TM.application.domain.model.shared`; `candidate_policy_targets(name: TableName, table_uuid: str) -> tuple[PolicyTarget, ...]`, `enclosing_policy_targets(catalog: str, namespace: str | None) -> tuple[PolicyTarget, ...]`, `nearest_attached[T](candidates: Sequence[PolicyTarget], attached: Mapping[str, T]) -> tuple[PolicyTarget, T] | None` (keys are `PolicyTarget.key()`) from `TM.application.domain.service.shared`; `checked_policy_name(value: str) -> str` (raises `ValueError` with today's two messages); `policy_target_from_request(...)`, `scope_target_in_listing(...)` (signatures unchanged) and `target_in_catalog(target: PolicyTarget, gateway: ReadTableMetadataGateway, tables_repo: TablesRepo, listings: dict[str, list[TableMetadataRef] | None]) -> bool` (the body of today's `ListTableMaintenancePolicyAttachmentsService._in_catalog` and `_table_in_catalog`) from `TM.application.service.shared`.

- [ ] **Step 1: Write the failing tests**

```python
def test_nearest_attached_prefers_the_first_candidate_that_is_attached():
    table, ns, catalog = candidate_policy_targets(TableName(catalog="iceberg", namespace="sales", table="orders"), "u1")
    assert nearest_attached((table, ns, catalog), {ns.key(): "A", catalog.key(): "B"}) == (ns, "A")

def test_nearest_attached_is_none_when_nothing_is_attached(): ...   # {} → None
def test_checked_policy_name_refuses_an_id_shaped_name(): ...       # "dp-01h2xcejqtf2nbrexx3vqjhp41" → ValueError
def test_checked_policy_name_refuses_a_space(): ...                 # "a b" → ValueError
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/domain -k "nearest_attached or checked_policy_name" -v`
Expected: FAIL, import errors.

- [ ] **Step 3: Implement the moves and the three new functions.** Re-export from each `shared/__init__.py`; delete the old modules (no shims). The web DTO move keeps the class names, so `openapi.json` must not change: `task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api` then `git -C /Users/kcl/Projects/retail-lakehouse diff --stat -- src/data-platform/backend/openapi.json` shows nothing.

- [ ] **Step 4: Run them and watch them pass**, then `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.

- [ ] **Step 5: Commit** `refactor(table-maintenance): move policy targets and the nearest-attachment walk to shared (KCL-71)`

### Task 2: The `TableDiscoveryPolicy` aggregate

**Files:**
- Create in `TM/application/domain/model/table_discovery_policy/`: `table_discovery_policy_id.py`, `default_discovery_policy_id.py`, `default_discovery_policy_name.py`, `table_discovery_policy_name.py`, `discovery_outcome.py`, `discovery_attribute.py`, `condition_operator.py`, `discovery_condition.py`, `discovery_rule.py`, `discovery_decision.py`, `discovery_policy_content.py`, `table_discovery_policy_version.py`, `table_discovery_policy.py`, `stale_discovery_policy_version.py`, `default_discovery_policy_is_fixed.py`, `__init__.py`
- Move: `TM/application/domain/model/table_discovery_rules/table_discovery_rule_id.py` and `unknown_discovery_rule_id.py` into the new package; the old package re-exports them from it (`from …table_discovery_policy import TableDiscoveryRuleId`). Delete `table_discovery_rules_id.py`: the old aggregate's `id` becomes `TableDiscoveryPolicyId` and `GLOBAL_TABLE_DISCOVERY_RULES_ID` becomes an alias of `DEFAULT_DISCOVERY_POLICY_ID` until Task 13 (one class per prefix: `tests/architecture/test_prefixed_ids.py` refuses `dp` twice)
- Create: `TM/application/port/outbound/table_discovery_policy/{__init__,table_discovery_policies_repo}.py` (the abstract port only; every aggregate needs exactly one repository port, `test_each_aggregate_has_one_repository_port_per_context`; Task 4 implements it)
- Modify: `TM/application/domain/model/table/table.py` imports `TableDiscoveryRuleId` from the new package; `tests/architecture/test_prefixed_ids.py` (`TableDiscoveryRulesId` → `TableDiscoveryPolicyId: "dp"`); `tests/architecture/test_aggregates.py` (adds `table_discovery_policy`); `TM/application/service/shared/translate_domain_errors.py` (`StaleDiscoveryPolicyVersion`, `DefaultDiscoveryPolicyIsFixed` → `ConflictError`)
- Test: `tests/…/domain/model/table_discovery_policy/test_discovery_policy_content.py`, `test_table_discovery_policy.py`

**Interfaces:**
- Produces:
  - `TableDiscoveryPolicyId(EntityId)`, `PREFIX = "dp"`; `DEFAULT_DISCOVERY_POLICY_ID = TableDiscoveryPolicyId("dp-00000000000000000000000000")`; `DEFAULT_DISCOVERY_POLICY_NAME = "default"`; `TableDiscoveryPolicyName(ValueObject)` with `value: str` checked by `checked_policy_name`.
  - `DiscoveryOutcome(StrEnum)`: `MANAGE = "manage"`, `UNMANAGE = "unmanage"`. `DiscoveryAttribute(StrEnum)`: `NAMESPACE = "namespace"`, `TABLE = "table"`. `ConditionOperator(StrEnum)`: `GLOB = "glob"`.
  - `DiscoveryCondition(ValueObject)`: `attribute`, `operator`, `values: tuple[str, ...]`; `matches(name: TableName) -> bool`.
  - `DiscoveryRule(ValueObject)`: `id: TableDiscoveryRuleId`, `outcome: DiscoveryOutcome`, `conditions: tuple[DiscoveryCondition, ...]`; `matches(name: TableName) -> bool` (all conditions).
  - `DiscoveryDecision(ValueObject)`: `outcome: DiscoveryOutcome`, `rule_id: TableDiscoveryRuleId | None`; property `manages -> bool`.
  - `DiscoveryPolicyContent(ValueObject)`: `description: str = ""`, `rules: tuple[DiscoveryRule, ...] = ()`, `no_match_outcome: DiscoveryOutcome`; `platform_default() -> DiscoveryPolicyContent` (classmethod, the default's content from Global Constraints); `decide(name: TableName) -> DiscoveryDecision`; `can_manage() -> bool`; `rule_ids() -> frozenset[TableDiscoveryRuleId]`. Wire form is exactly the Global Constraints JSON (`from_primitives` / `to_primitives`).
  - `TableDiscoveryPolicyVersion(ValueObject)`: `policy_id`, `version: PositiveInt`, `content`, `created_at`.
  - `TableDiscoveryPolicy(AggregateRoot[TableDiscoveryPolicyId])`: `id`, `name`, `content`, `version: PositiveInt`, `created_at`, `updated_at`; `create(name, content, now)` (new `dp-` id, version 1); `create_default(now)`; `replace(content, expected_version: int, now, *, new_rule_ids: Collection[TableDiscoveryRuleId] = ()) -> None`; `current_version() -> TableDiscoveryPolicyVersion`; property `is_default`; `decide(name)` and `can_manage()` delegate to the content.
  - `StaleDiscoveryPolicyVersion(ValueError)`, `DefaultDiscoveryPolicyIsFixed(ValueError)`, `UnknownDiscoveryRuleId(ValueError)`.
  - `TableDiscoveryPoliciesRepo(Repository[TableDiscoveryPolicy])`, methods as listed in Task 4.

- [ ] **Step 1: Write the failing tests**

```python
def _rule(rule_id, outcome, **globs):  # globs: namespace=[...], table=[...]
    return {"id": rule_id, "outcome": outcome,
            "conditions": [{"attribute": a, "operator": "glob", "values": v} for a, v in globs.items()]}

ORDERS = TableName(catalog="iceberg", namespace="sales.eu", table="orders_tmp")

def test_first_matching_rule_decides():
    content = DiscoveryPolicyContent.from_primitives({"no_match_outcome": "unmanage", "rules": [
        _rule(R1, "manage", table=["orders_tmp"]), _rule(R2, "unmanage", table=["*_tmp"])]})
    assert content.decide(ORDERS) == DiscoveryDecision(outcome=DiscoveryOutcome.MANAGE, rule_id=TableDiscoveryRuleId(R1))

def test_no_match_uses_the_no_match_outcome_without_a_rule(): ...   # rules () , "manage" → (MANAGE, None)
def test_every_condition_must_hold(): ...                            # namespace ["sales"] + table ["orders_*"] misses "sales.eu"
def test_namespace_glob_crosses_dots(): ...                           # ["sales.*"] matches "sales.eu"
def test_glob_is_case_sensitive(): ...                                # ["Orders*"] misses "orders_tmp"
def test_a_rule_needs_a_condition(): ...                              # conditions [] → InvariantViolation
def test_an_attribute_appears_once_per_rule(): ...                    # two "table" conditions → InvariantViolation
def test_empty_values_or_an_empty_glob_are_refused(): ...             # [] and [""] → InvariantViolation
def test_unknown_attribute_or_operator_is_refused(): ...              # "label", "regex" → InvariantViolation
def test_rule_ids_are_unique(): ...                                   # same id twice → InvariantViolation
def test_can_manage(): ...  # default False; manage rule True; no rules + "manage" True; only unmanage rules + "unmanage" False
def test_content_round_trips_its_wire_form(): ...                     # to_primitives(from_primitives(x)) == x

def test_replace_keeps_known_ids_and_accepts_declared_new_ones(): ...  # version 2, content replaced, updated_at moved
def test_replace_refuses_an_id_the_policy_does_not_hold():
    policy = TableDiscoveryPolicy.create(NAME, content_with(R1), T0)
    with pytest.raises(UnknownDiscoveryRuleId, match=R2):
        policy.replace(content_with(R2), 1, T1)
    assert policy.version == 1
def test_replace_refuses_a_stale_version(): ...                       # expected 3 at version 1 → StaleDiscoveryPolicyVersion
def test_default_cannot_be_replaced(): ...                            # create_default(T0).replace(...) → DefaultDiscoveryPolicyIsFixed
def test_default_has_the_fixed_id_name_and_content(): ...             # is_default, name "default", no rules, unmanage
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/domain/model/table_discovery_policy -v`
Expected: FAIL, package not importable.

- [ ] **Step 3: Implement.** `DiscoveryCondition.matches` reads `name.namespace` or `name.table` by attribute and `any(fnmatchcase(value, glob) for glob in values)`. The default's `replace` check comes before the version check.

- [ ] **Step 4: Run them and watch them pass**, then `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.

- [ ] **Step 5: Commit** `feat(table-maintenance): add the versioned discovery policy aggregate (KCL-71)`

### Task 3: The `TableDiscoveryPolicyAttachment` aggregate and discovery resolution

**Files:**
- Create: `TM/application/domain/model/table_discovery_policy_attachment/{__init__,table_discovery_policy_attachment_id,table_discovery_policy_attachment}.py`; `TM/application/domain/service/table_discovery_policy_attachment/{__init__,decide_table_discovery,scanned_catalogs}.py`; `TM/application/port/outbound/table_discovery_policy_attachment/{__init__,table_discovery_policy_attachments_repo}.py` (abstract port only, methods as listed in Task 4)
- Modify: `tests/architecture/test_prefixed_ids.py` (`TableDiscoveryPolicyAttachmentId: "da"`), `tests/architecture/test_aggregates.py` (adds `table_discovery_policy_attachment`)
- Test: `tests/…/domain/model/table_discovery_policy_attachment/test_table_discovery_policy_attachment.py`, `tests/…/domain/service/table_discovery_policy_attachment/test_decide_table_discovery.py`, `test_scanned_catalogs.py`

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces:
  - `TableDiscoveryPolicyAttachmentId(EntityId)`, `PREFIX = "da"`.
  - `TableDiscoveryPolicyAttachment(AggregateRoot[TableDiscoveryPolicyAttachmentId])`: `id`, `target: PolicyTarget`, `policy_id: TableDiscoveryPolicyId`, `attached_at`; `attach(target, policy_id, now)` (new `da-` id); `replace_policy(policy_id, now)`; property `catalog -> str` (`target.path[0]`).
  - `decide_table_discovery(name: TableName, table_uuid: str, attachments: Iterable[TableDiscoveryPolicyAttachment], policies: Mapping[TableDiscoveryPolicyId, TableDiscoveryPolicy]) -> DiscoveryDecision`: `nearest_attached(candidate_policy_targets(name, table_uuid), …)`; the found policy decides; no attachment, or an attachment whose policy is not in `policies`, decides by `DiscoveryPolicyContent.platform_default()`.
  - `scanned_catalogs(attachments: Iterable[TableDiscoveryPolicyAttachment], policies: Mapping[TableDiscoveryPolicyId, TableDiscoveryPolicy]) -> tuple[str, ...]`: sorted, unique catalogs of the attachments whose policy `can_manage()`.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_table_attachment_beats_a_managing_catalog():
    decision = decide_table_discovery(ORDERS, "u1",
        [attached(catalog_target("iceberg"), MANAGE_ALL), attached(table_target(ORDERS, "u1"), DEFAULT)],
        {MANAGE_ALL.id: MANAGE_ALL, DEFAULT.id: DEFAULT})
    assert decision.outcome is DiscoveryOutcome.UNMANAGE

def test_the_deepest_namespace_wins(): ...           # "sales" manage, "sales.eu" unmanage → unmanage for sales.eu.orders
def test_nothing_attached_is_unmanaged(): ...        # [] → (UNMANAGE, None)
def test_a_table_is_found_by_uuid_not_by_path(): ... # table target path of an old name, same uuid → its policy decides
def test_a_missing_policy_falls_back_to_the_default(): ...

def test_a_catalog_is_scanned_when_a_policy_in_it_can_manage():
    assert scanned_catalogs(
        [attached(namespace_target("iceberg", "sales"), MANAGE_ALL), attached(catalog_target("other"), DEFAULT)],
        {MANAGE_ALL.id: MANAGE_ALL, DEFAULT.id: DEFAULT},
    ) == ("iceberg",)
def test_scanned_catalogs_are_sorted_and_unique(): ...
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/domain -k "discovery_policy_attachment or decide_table_discovery or scanned_catalogs" -v`
Expected: FAIL, not importable.

- [ ] **Step 3: Implement.**

- [ ] **Step 4: Run them and watch them pass**, then `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.

- [ ] **Step 5: Commit** `feat(table-maintenance): add discovery policy attachments and resolve the nearest one (KCL-71)`

### Task 4: Store discovery policies and attachments

**Files:**
- Create: `TM/adapter/outbound/table_discovery_policy/sql/{__init__,table_discovery_policies_table,table_discovery_policy_versions_table,table_discovery_policy_row_mapper,table_discovery_policies_sql_repo}.py` (+ package `__init__`); `TM/adapter/outbound/table_discovery_policy_attachment/sql/{__init__,table_discovery_policy_attachments_table,table_discovery_policy_attachment_row_mapper,table_discovery_policy_attachments_sql_repo}.py` (+ package `__init__`); `tests/context/table_maintenance/fakes/in_memory_table_discovery_policies_repo.py`, `in_memory_table_discovery_policy_attachments_repo.py`; `TM/application/port/inbound/table_discovery_policy/ensure_default_table_discovery_policy/`, `TM/application/service/table_discovery_policy/ensure_default_table_discovery_policy.py`
- Modify: `TM/adapter/outbound/shared/sql/create_schema.py` (`AGGREGATE_SQL_PACKAGES` adds both packages), `bootstrap/container/repositories.py`, `build_repositories.py`, `run_migrations.py` (seed the default discovery policy after the maintenance one)
- Test: `tests/…/adapter/outbound/table_discovery_policy/test_table_discovery_policies_sql_repo.py`, `tests/…/adapter/outbound/table_discovery_policy_attachment/test_table_discovery_policy_attachments_sql_repo.py`, the drift test `tests/…/adapter/outbound/shared/sql/test_create_schema.py`, `tests/bootstrap/container/test_run_migrations.py`, the ensure-default service test

**Interfaces:**
- Consumes: Tasks 2 and 3 (the two repository ports below are declared there with these methods; this task writes their SQL adapters and in-memory fakes).
- Produces:
  - `TableDiscoveryPoliciesRepo(Repository[TableDiscoveryPolicy])`: `get_by_name(name: TableDiscoveryPolicyName) -> TableDiscoveryPolicy | None`, `get_many(ids: Sequence[EntityId]) -> list[TableDiscoveryPolicy]`, `update(policy) -> TableDiscoveryPolicy` (writes the version row in the same transaction; `StaleDiscoveryPolicyVersion` when the stored version is not `policy.version - 1`), `get_version(policy_id: EntityId, version: int) -> TableDiscoveryPolicyVersion | None`, `delete(entity_id) -> None` (`ConflictError` while attached). `create` of a taken name is `ConflictError`.
  - `TableDiscoveryPolicyAttachmentsRepo(Repository[TableDiscoveryPolicyAttachment])`: `get_by_target(target)`, `get_many_by_targets(targets)`, `list_in_catalog(catalog: str) -> list[…]`, `list_for_policy(policy_id) -> list[…]`, `has_attachments_for_policy(policy_id) -> bool`, `update(attachment)`, `delete(entity_id)`. A second `create` on the same `target.key()` is `ConflictError`.
  - Tables: `table_discovery_policies` (`id` pk, `name` unique, `version`, `created_at`, `updated_at`); `table_discovery_policy_versions` (`policy_id` fk + `version` pk, `content_json` JSON, `created_at`); `table_discovery_policy_attachments` (`id` pk, `target_key` unique, `target_type`, `path_json`, `table_uuid` nullable, `catalog` indexed, `policy_id` fk indexed, `attached_at`), as the maintenance tables are.
  - `EnsureDefaultTableDiscoveryPolicyUseCase` (input and output empty), service `EnsureDefaultTableDiscoveryPolicyService(policies_repo, *, clock=...)`: creates the default when `get(DEFAULT_DISCOVERY_POLICY_ID)` is None; idempotent.

- [ ] **Step 1: Write the failing tests** (SQLite through the existing repo-test engine fixture; the fakes get the same tests through a parametrised fixture, as the maintenance repos do)

```python
def test_update_writes_a_version_and_keeps_the_old_one(repo): ...   # v1 and v2 both readable by get_version
def test_update_from_a_stale_copy_is_refused(repo): ...             # two copies, second update → StaleDiscoveryPolicyVersion
def test_a_taken_name_conflicts(repo): ...                          # ConflictError
def test_delete_while_attached_conflicts(repos): ...                # ConflictError, policy still there
def test_one_attachment_per_target(attachments): ...                # second create same key → ConflictError
def test_list_in_catalog_returns_only_that_catalog(attachments): ...
def test_a_table_target_round_trips_its_uuid(attachments): ...
def test_migrate_seeds_the_default_discovery_policy(): ...          # run_migrations then get(DEFAULT_DISCOVERY_POLICY_ID) is default
def test_ensure_default_twice_keeps_one(): ...
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/adapter/outbound/table_discovery_policy tests/context/table_maintenance/adapter/outbound/table_discovery_policy_attachment tests/bootstrap/container/test_run_migrations.py -v`
Expected: FAIL, modules missing.

- [ ] **Step 3: Implement**, copying the maintenance repos' transaction and integrity-error handling.

- [ ] **Step 4: Run them and watch them pass**, then `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.

- [ ] **Step 5: Commit** `feat(table-maintenance): store discovery policies, their versions and attachments (KCL-71)`

### Task 5: Discovery policy use cases and `/v1/discovery-policies`

**Files:**
- Create: under `TM/application/port/inbound/table_discovery_policy/` the use case packages `create_table_discovery_policy/`, `get_table_discovery_policy/`, `list_table_discovery_policies/`, `update_table_discovery_policy/`, `delete_table_discovery_policy/`, `get_table_discovery_policy_version/` (each `__init__`, `input`, `output`, `use_case`); under `TM/application/service/table_discovery_policy/` one service file per package of the same name, plus `table_discovery_policy_output_fields.py` and `content_with_minted_rule_ids.py`; `TM/adapter/inbound/web/table_discovery_policy/{__init__,dto,router}.py`
- Modify: `TM/adapter/inbound/web/register_routes.py`, `TM/adapter/inbound/web/shared/web_use_cases.py`, `bootstrap/container/use_cases.py`, `build_use_cases.py`, `build_web_use_cases.py`, `openapi.json` and the generated client (`task -d /Users/kcl/Projects/retail-lakehouse dev:generate-api`)
- Test: `tests/…/application/service/table_discovery_policy/test_table_discovery_policy_services.py`, `tests/…/adapter/inbound/web/table_discovery_policy/test_table_discovery_policy_routes.py`

**Interfaces:**
- Consumes: Task 4.
- Produces:
  - Inputs: `CreateTableDiscoveryPolicyUseCaseInput(name: str, content: dict[str, Any])`; `GetTableDiscoveryPolicyUseCaseInput(name: str)`; `ListTableDiscoveryPoliciesUseCaseInput()`; `UpdateTableDiscoveryPolicyUseCaseInput(name: str, content: dict[str, Any], version: int)`; `DeleteTableDiscoveryPolicyUseCaseInput(name: str)`; `GetTableDiscoveryPolicyVersionUseCaseInput(name: str, version: int)`. `content` is the Global Constraints JSON; a rule may omit `id`.
  - Outputs carry `id`, `name`, `is_default`, `version`, `content: dict[str, Any]`, `created_at`, `updated_at` (the version output: `created_at` of the version, no `updated_at`); the list output's nested `TableDiscoveryPolicy` adds `attachment_count: int`.
  - `content_with_minted_rule_ids(content: dict[str, Any], new_id: Callable[[], str]) -> tuple[dict[str, Any], frozenset[str]]`: gives every rule without `id` (or with `id: null`) a minted `dr-` id and returns the ids it minted. A rule sent with `"id": ""` is refused 422 `a rule id is a dr- id or absent` (fixes the follow-up noted under KCL-73).
  - Routes and DTOs (router functions name the operation ids): `list_table_discovery_policies` `GET /discovery-policies` → `TableDiscoveryPoliciesApiResponse{policies: list[ListedTableDiscoveryPolicyApiResponse]}`; `create_table_discovery_policy` `POST` (201) body `CreateTableDiscoveryPolicyApiRequest{name, description="", no_match_outcome, rules}`; `get_table_discovery_policy`, `update_table_discovery_policy` (`UpdateTableDiscoveryPolicyApiRequest{version, description, no_match_outcome, rules}`), `delete_table_discovery_policy` (204) on `/discovery-policies/{name}`; `get_table_discovery_policy_version` on `/discovery-policies/{name}/versions/{version}` → `TableDiscoveryPolicyVersionApiResponse`. `TableDiscoveryPolicyApiResponse{id, name, is_default, version, created_at, updated_at, description, no_match_outcome, rules: list[DiscoveryRuleApiResponse]}`; `DiscoveryRuleApiRequest{id: str | None = None, outcome: Literal["manage", "unmanage"], conditions: list[DiscoveryConditionApiRequest]}`; `DiscoveryConditionApiRequest{attribute: Literal["namespace", "table"], operator: Literal["glob"], values: list[str]}`, and their `…ApiResponse` twins. Every request DTO `extra="forbid"`.

- [ ] **Step 1: Write the failing tests**

```python
def test_create_mints_rule_ids_and_starts_at_version_1(services): ...   # every rules[i]["id"] matches ^dr-
def test_create_with_a_taken_name_conflicts(services): ...
def test_update_keeps_ids_of_unchanged_rules_and_bumps_the_version(services): ...
def test_update_with_another_policys_rule_id_is_refused(services):
    other = services.create(name="other", content=one_rule())
    with pytest.raises(ValidationError, match="unknown discovery rule id"):
        services.update(name="mine", version=1, content=content_with_rule_id(other.content["rules"][0]["id"]))
    assert services.get(name="mine").version == 1
def test_update_from_a_stale_version_conflicts(services): ...
def test_update_of_the_default_conflicts(services): ...
def test_delete_of_the_default_or_an_attached_policy_conflicts(services): ...
def test_a_version_stays_readable_after_an_update(services): ...       # get_version(name, 1) is the old content
def test_list_counts_attachments(services): ...

def test_post_then_get_round_trips_the_body(client): ...               # rule order and conditions unchanged
def test_put_with_an_empty_rule_id_is_422(client): ...
def test_put_with_two_table_conditions_is_422(client): ...
def test_put_default_is_409(client): ...
def test_get_unknown_policy_is_404(client): ...
def test_get_version_0_is_404(client): ...
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/service/table_discovery_policy tests/context/table_maintenance/adapter/inbound/web/table_discovery_policy -v`
Expected: FAIL.

- [ ] **Step 3: Implement**, mirroring the maintenance policy services and router (`_policy_response` flattens `content` into the response). Names are checked through `TableDiscoveryPolicyName` inside `translate_domain_errors`. Regenerate the client.

- [ ] **Step 4: Run them and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend` (its contract test checks `openapi.json` against the generated client).

- [ ] **Step 5: Commit** `feat(table-maintenance): create, edit and version discovery policies through the API (KCL-71)`

### Task 6: Attach discovery policies, list scanned catalogs, refuse unreadable catalogs

**Files:**
- Create: `TM/application/port/inbound/table_discovery_policy_attachment/{attach_table_discovery_policy,detach_table_discovery_policy,list_table_discovery_policy_attachments,list_scanned_catalogs}/`; `TM/application/service/table_discovery_policy_attachment/` with the four services; `TM/adapter/inbound/web/table_discovery_policy_attachment/{__init__,dto,router}.py`; `TM/application/port/outbound/table/read_table_metadata/catalog_access_denied_error.py`
- Modify: `TM/adapter/outbound/table/pyiceberg/read_table_metadata_pyiceberg_gateway.py` (map PyIceberg `ForbiddenError` and `UnauthorizedError` on open, list and load to `CatalogAccessDeniedError`), `TM/adapter/inbound/web/error_handlers.py` (`CatalogAccessDeniedError` → 403), `tests/architecture/test_outbound_port_structure.py` (`GATEWAY_EXTRA_FILES` adds `catalog_access_denied_error.py`), `TM/application/service/shared/policy_target_from_request.py` (re-raises `CatalogAccessDeniedError` untouched, so it is 403 for maintenance attachments too), `tests/context/table_maintenance/fakes/fake_read_table_metadata_gateway.py` (can deny a catalog), the wiring files of Task 5, the list service of Task 5 (`attachment_count` from `list_for_policy`), `openapi.json` + client
- Test: `tests/…/application/service/table_discovery_policy_attachment/test_discovery_attachment_services.py`, `tests/…/adapter/inbound/web/table_discovery_policy_attachment/test_discovery_attachment_routes.py`, the PyIceberg gateway test

**Interfaces:**
- Consumes: Tasks 1, 3, 4, 5.
- Produces:
  - `AttachTableDiscoveryPolicyUseCaseInput(policy_name: str, target_type: str, path: tuple[str, ...])` → output `(target_type, path, table_uuid, policy_id, policy_name, attached_at)`; `DetachTableDiscoveryPolicyUseCaseInput(policy_name: str, target_type: str, path: tuple[str, ...], table_uuid: str | None = None)`; `ListTableDiscoveryPolicyAttachmentsUseCaseInput(policy_name: str)` → items `(type, path, table_uuid, policy_id, policy_name, attached_at, orphaned)`; `ListScannedCatalogsUseCaseInput()` → `catalogs: tuple[str, ...]` (from `scanned_catalogs(attachments_repo.list_all(), policies by id)`).
  - Attach replaces what is attached on the target; detach of a target holding another policy, or nothing, is 404 (maintenance's rules).
  - `class CatalogAccessDeniedError(Exception)` with `__init__(self, catalog: str)` and the message from Global Constraints.
  - Routes (tag `discovery-policies`): `list_table_discovery_policy_attachments`, `attach_table_discovery_policy` (200), `detach_table_discovery_policy` (204) on `/discovery-policies/{name}/attachments`; `list_scanned_catalogs` `GET /scanned-catalogs`. DTOs `AttachTableDiscoveryPolicyApiRequest{target: PolicyTargetApiRequest}`, `DetachTableDiscoveryPolicyApiRequest{target: DetachPolicyTargetApiRequest}`, `TableDiscoveryPolicyAttachmentApiResponse{target: PolicyTargetApiResponse, policy_id, policy_name, attached_at}`, `ListedTableDiscoveryPolicyAttachmentApiResponse` (+ `orphaned`), `TableDiscoveryPolicyAttachmentsApiResponse{attachments}`, `ScannedCatalogsApiResponse{catalogs: list[str]}`.

- [ ] **Step 1: Write the failing tests**

```python
def test_attach_to_a_table_resolves_its_uuid_from_the_catalog(services): ...  # table_uuid set; table need not be managed
def test_attach_replaces_the_targets_policy(services): ...
def test_attach_to_a_missing_namespace_is_not_found(services): ...
def test_attach_in_an_unreadable_catalog_is_access_denied(services):
    services.catalog.deny("secret")
    with pytest.raises(CatalogAccessDeniedError, match="cannot read catalog secret"):
        services.attach(policy_name="p", target_type="catalog", path=("secret",))
def test_detach_names_the_attached_policy_or_is_not_found(services): ...
def test_list_marks_a_target_that_left_the_catalog_orphaned(services): ...
def test_scanned_catalogs_follow_managing_attachments(services): ...         # default on "a", manage policy on "b.ns" → ("b",)

def test_put_attachment_in_an_unreadable_catalog_is_403(client): ...        # detail names the catalog
def test_get_scanned_catalogs(client): ...                                   # {"catalogs": [...]}
def test_pyiceberg_forbidden_maps_to_access_denied(): ...                     # factory raising ForbiddenError → CatalogAccessDeniedError
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/service/table_discovery_policy_attachment tests/context/table_maintenance/adapter/inbound/web/table_discovery_policy_attachment tests/context/table_maintenance/adapter/outbound/table -v`
Expected: FAIL.

- [ ] **Step 3: Implement**, mirroring the maintenance attachment services with Task 1's shared helpers. Regenerate the client.

- [ ] **Step 4: Run them and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.

- [ ] **Step 5: Commit** `feat(table-maintenance): attach discovery policies and list the scanned catalogs (KCL-71)`

### Task 7: Scans decide by the nearest discovery policy

**Files:**
- Create: `TM/application/service/table/discovery_decider.py`
- Modify: `TM/application/domain/model/table/table.py` (`register` and `manage` take `TableDiscoveryRuleId | None`), `TM/application/domain/service/table/decide_table_management.py`, `TM/application/service/table/register_discovered_table.py`, `apply_discovery_to_known_table.py`, `sync_discovered_tables.py`, `process_table_hint.py`, `bootstrap/container/build_use_cases.py` (the two services get the discovery repos instead of the rules repo)
- Test: `tests/…/domain/service/table/test_decide_table_management.py`, `tests/…/domain/model/table/test_table.py`, `tests/…/application/service/table/test_discovery_sync_services.py`, the process-hint tests in `test_table_services.py`, `tests/context/table_maintenance/application/service/conftest.py`

**Interfaces:**
- Consumes: Tasks 3 and 4.
- Produces:
  - `class DiscoveryDecider` with `for_catalog(cls, catalog: str, attachments_repo: TableDiscoveryPolicyAttachmentsRepo, policies_repo: TableDiscoveryPoliciesRepo) -> DiscoveryDecider` (one `list_in_catalog` and one `get_many`), `for_table(cls, name: TableName, table_uuid: str, attachments_repo, policies_repo) -> DiscoveryDecider` (one `get_many_by_targets(candidate_policy_targets(...))`), and `decide(name: TableName, table_uuid: str) -> DiscoveryDecision` (calls `decide_table_discovery`).
  - `decide_table_management(table: Table, decision: DiscoveryDecision, now: datetime) -> TableManagementChange` (a manage decision manages under `decision.rule_id`, else unmanages; `RULE_CHANGED` when a managed table's deciding rule id changes, including to or from `None`).
  - `register_discovered_table(found, decision: DiscoveryDecision, tables_repo, table_change_gateway, change, now)`; `apply_discovery_to_known_table(table, name, decision: DiscoveryDecision, …)` (the caller decides with the new name and the table's uuid).
  - `SyncDiscoveredTablesService(tables_repo, discovery_policies_repo, discovery_attachments_repo, discoveries_repo, catalog_gateway, table_change_gateway, *, clock)`; `ProcessTableHintService(tables_repo, discovery_policies_repo, discovery_attachments_repo, catalog_gateway, table_change_gateway, discovery_request_gateway, *, clock)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_namespace_policy_manages_its_tables_under_the_deciding_rule(sync): ...  # managed, matched_rule_id == R1
def test_a_table_policy_overrides_its_namespace(sync): ...                         # default on the table → unmanaged
def test_no_attachment_registers_unmanaged_and_sends_nothing(sync): ...
def test_managed_by_the_no_match_outcome_has_no_rule(sync): ...                    # matched_rule_id is None
def test_a_renamed_table_keeps_its_table_attachment(sync):
    attach(table_target(old_name, "u1"), MANAGE_ALL); catalog.rename("u1", new_namespace="other")
    out = sync.execute(SyncDiscoveredTablesUseCaseInput(catalog="iceberg", namespace=None))
    assert tables.get(TableId("u1")).is_managed and out.renamed == 1
def test_the_scan_reads_attachments_once_per_catalog(sync): ...                    # attachments fake records one list_in_catalog call
def test_a_hint_in_an_unscanned_catalog_registers_unmanaged(hint): ...            # action "registered", no table change sent
def test_rule_change_moves_matched_rule_id(): ...                                  # decide_table_management → RULE_CHANGED
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/application/service/table tests/context/table_maintenance/application/domain/service/table -v`
Expected: FAIL.

- [ ] **Step 3: Implement.** The old rules aggregate is no longer read by any scan; it and its API stay until Task 13 because the console still calls them.

- [ ] **Step 4: Run them and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.

- [ ] **Step 5: Commit** `feat(table-maintenance): decide each discovered table by its nearest discovery policy (KCL-71)`

### Task 8: The scanned catalogs drive the schedules, and every change rescans

**Files:**
- Create: `TM/application/port/outbound/table_discovery_policy_attachment/sync_scanned_catalogs/{__init__,gateway,input}.py`; `TM/adapter/hybrid/temporal/outbound/table_discovery_policy_attachment/{__init__,sync_scanned_catalogs_temporal_gateway,catalog_scan_schedule}.py`; `TM/application/port/inbound/table_discovery_policy_attachment/sync_scanned_catalogs/`, `TM/application/service/table_discovery_policy_attachment/sync_scanned_catalogs.py`, `apply_discovery_change.py`; `tests/context/table_maintenance/fakes/recording_sync_scanned_catalogs_gateway.py`
- Delete: `TM/adapter/hybrid/temporal/inbound/ensure_table_discovery_schedule.py` and its test (its schedule body moves to `catalog_scan_schedule.py`)
- Modify: `TM/application/port/outbound/table/send_discovery_request/input.py` (`rules_version` → `change_id: str | None = None`), `TM/adapter/hybrid/temporal/contracts/table_discovery/workflow_id.py` (`change_id`), `send_discovery_request_temporal_gateway.py`, the update / attach / detach services of Tasks 5 and 6, the old `replace_table_discovery_rules.py` (sends `change_id=f"rules-v{version}"` until Task 13), `bootstrap/configs/app_settings.py` (`discovery_interval_seconds: int = Field(default=600, ge=60, le=86400)`), `bootstrap/container/gateways.py`, `build_gateways.py`, `apply_worker_startup.py`, `bootstrap/worker.py`, `tests/bootstrap/configs/test_app_settings.py`
- Test: `tests/…/adapter/hybrid/temporal/outbound/table_discovery_policy_attachment/test_sync_scanned_catalogs_temporal_gateway.py` (Temporal test server, as the old ensure test did), `tests/…/application/service/table_discovery_policy_attachment/test_apply_discovery_change.py`, `tests/…/adapter/hybrid/temporal/contracts/test_workflow_ids.py`, `tests/bootstrap/container/test_apply_worker_startup.py`, `tests/…/adapter/hybrid/temporal/outbound/table/test_send_discovery_request_temporal_gateway.py`

**Interfaces:**
- Consumes: Tasks 3 to 7.
- Produces:
  - `@dataclass(frozen=True) class SyncScannedCatalogsGatewayInput: catalogs: list[str]`; `SyncScannedCatalogsGateway.sync(input: SyncScannedCatalogsGatewayInput) -> None` (abstract): afterwards exactly these catalogs have a scan schedule.
  - `SyncScannedCatalogsTemporalGateway(client: Client, bridge: AsyncLoopBridge, *, interval: timedelta)`: lists schedules (`client.list_schedules()`), keeps those whose id starts with `TABLE_DISCOVERY_SCHEDULE_ID_PREFIX`, creates or updates-and-unpauses each wanted one (today's create / `ScheduleAlreadyRunningError` → update / unpause), deletes each listed one not wanted. `catalog_scan_schedule(catalog: str, *, interval: timedelta) -> Schedule` is today's `_schedule`.
  - `SyncScannedCatalogsUseCaseInput()` → `SyncScannedCatalogsUseCaseOutput(catalogs: tuple[str, ...])`; `SyncScannedCatalogsService(policies_repo, attachments_repo, catalog_scans: SyncScannedCatalogsGateway)` (errors propagate: the worker start must fail loudly).
  - `apply_discovery_change[T](policies_repo, attachments_repo, discovery_requests: SendDiscoveryRequestGateway, catalog_scans: SyncScannedCatalogsGateway, change: Callable[[], T], *, affected_catalogs: Collection[str], change_id: str) -> T`: before = `scanned_catalogs(...)`; `result = change()`; after = `scanned_catalogs(...)`; `catalog_scans.sync(sorted(after))` (exception logged); for each catalog in `sorted(set(affected_catalogs) & (before | after))` send `SendDiscoveryRequestGatewayInput(catalog, None, change_id=change_id)` (each exception logged); return `result`.
  - Update, attach and detach services take `discovery_requests`, `catalog_scans` and `new_change_id: Callable[[], str] = lambda: uuid.uuid4().hex`; update's affected catalogs are `{a.catalog for a in attachments_repo.list_for_policy(policy.id)}`, attach's and detach's are `{target.path[0]}`.
  - `table_discovery_adhoc_workflow_id(catalog, namespace, *, change_id: str | None = None)`: `…:trigger=policy-changed:change={change_id}` when given, `…:trigger=adhoc` otherwise.
  - `apply_worker_startup(client, settings, use_cases)` runs `await asyncio.to_thread(use_cases.sync_scanned_catalogs.execute, SyncScannedCatalogsUseCaseInput())` after the search-attribute check (the bridge would deadlock on its own loop thread); `run_worker` passes `use_cases`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_sync_creates_wanted_and_deletes_unwanted_schedules(temporal_client, bridge):
    await create_schedule(temporal_client, table_discovery_schedule_id("old"))
    await to_thread(gateway.sync, SyncScannedCatalogsGatewayInput(catalogs=["iceberg"]))
    assert await discovery_schedule_ids(temporal_client) == {"table-discovery:catalog=iceberg"}
async def test_sync_rewrites_the_interval_and_unpauses(temporal_client, bridge): ...
async def test_sync_leaves_other_schedules_alone(temporal_client, bridge): ...   # an unrelated schedule id survives

def test_detaching_the_last_managing_policy_rescans_and_drops_the_schedule():
    out = detach(...)   # catalog "iceberg" scanned before, not after
    assert scans.synced[-1] == [] and requests.sent == [SendDiscoveryRequestGatewayInput("iceberg", None, change_id=ID)]
def test_attaching_an_unmanage_policy_in_an_unscanned_catalog_scans_nothing(): ...   # synced [], sent []
def test_update_rescans_every_catalog_the_policy_is_attached_in(): ...
def test_a_failed_schedule_sync_still_saves_and_rescans(): ...                       # gateway raises; attachment stored; request sent
def test_a_refused_update_neither_syncs_nor_rescans(): ...                           # unknown rule id → ValidationError; synced [], sent []
def test_each_change_has_its_own_change_id(): ...
def test_change_id_names_the_adhoc_workflow(): ...    # "table-discovery:catalog=iceberg:trigger=policy-changed:change=ab12"
async def test_worker_startup_syncs_the_scanned_catalogs(): ...                      # use case called once, off the loop thread
def test_discovery_interval_below_60_is_refused(): ...                                # GLAC_DISCOVERY_INTERVAL_SECONDS=30 → ValidationError
```

- [ ] **Step 2: Run them and watch them fail**

Run: `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests/context/table_maintenance/adapter/hybrid/temporal tests/context/table_maintenance/application/service/table_discovery_policy_attachment tests/bootstrap -v`
Expected: FAIL.

- [ ] **Step 3: Implement.** `build_gateways` adds `sync_scanned_catalogs=SyncScannedCatalogsTemporalGateway(client, bridge, interval=timedelta(seconds=settings.discovery_interval_seconds))`. Temporal's schedule list is eventually consistent: a schedule just created may be missing from the listing, which only means it is not deleted, and creation never depends on the listing.

- [ ] **Step 4: Run them and watch them pass**, including `tests/architecture/test_temporal_workflow_sandbox.py` and `test_temporal_workflow_determinism.py`; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=backend`.

- [ ] **Step 5: Commit** `feat(table-maintenance): scan the catalogs discovery policies can manage and rescan after each change (KCL-71)`

### Task 9: Console: the Discovery policies list

**Files:**
- Create: `pages/DiscoveryPoliciesPage.tsx` (+ `.stories.tsx`, `.test.tsx`), `components/CreateDiscoveryPolicyDialog.tsx` (+ `.stories.tsx`, `.test.tsx`), `lib/discoveryPolicyPaths.ts`
- Modify: `AppRoutes.tsx` (`/discovery-policies`, and `/discovery-rules` → `<Navigate to="/discovery-policies" replace />`), `components/AppShell.tsx` (entry "Discovery policies", `IconRadar`, matches `/discovery-policies`), `AppShell.test.tsx`, `stories/storyData.ts` (`DISCOVERY_POLICIES`: `default`, and `sales-tables` with two rules, attached to namespace `iceberg.sales`), `stories/lakehouseHandlers.ts`
- Test: the files above

**Interfaces:**
- Consumes: the generated `discovery-policies` client of Tasks 5 and 6 (`useListTableDiscoveryPolicies`, `createTableDiscoveryPolicy`, `deleteTableDiscoveryPolicy`, `getListTableDiscoveryPoliciesQueryKey`).
- Produces: `discoveryPoliciesPath(): "/discovery-policies"`, `discoveryPolicyPath(name)`, `discoveryPolicyVersionPath(name, version)` (names `encodeURIComponent`-ed).

- [ ] **Step 1: Failing tests and stories.** The list (via `ResourceListPage`) shows the default first with a `Default` badge, then by name; columns Name, Description, When no rule matches (`Manage` / `Do not manage`), Rules (count, `tabular-nums`), Version, Attached to (count). A row links to its policy page. Delete uses `ConfirmDeleteDialog`, disabled for the default ("The default policy cannot be deleted.") and for an attached policy ("Detach it from every target before deleting it."). New policy opens `CreateDiscoveryPolicyDialog`: Name, Description, When no rule matches (`Select`, preselected `Do not manage`); a 409 shows the API's detail in the dialog; success navigates to the new policy's page. Stories: loaded, empty (only the default), error, phone width with `expectNoHorizontalPageScroll`; the old `/discovery-rules` URL lands on the list.
- [ ] **Step 2: Run and watch them fail:** `npm --prefix src/data-platform/frontend test -- --run DiscoveryPoliciesPage CreateDiscoveryPolicyDialog AppShell`
- [ ] **Step 3: Implement** with design-system parts only.
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`
- [ ] **Step 5: Commit** `feat(console): list and create discovery policies (KCL-71)`

### Task 10: Console: edit a discovery policy and read its versions

**Files:**
- Create: `pages/DiscoveryPolicyPage.tsx`, `pages/DiscoveryPolicyVersionPage.tsx` (each + `.stories.tsx`, `.test.tsx`), `components/DiscoveryRulesTable.tsx` (+ `.stories.tsx`, `.test.tsx`), `lib/discoveryPolicyDraft.ts` (+ `.test.ts`)
- Modify: `components/DiscoveryRuleEditor.tsx` (+ story, test) for the new rule shape, `AppRoutes.tsx` (two routes), `stories/lakehouseHandlers.ts`
- Test: the files above

**Interfaces:**
- Consumes: `useGetTableDiscoveryPolicy`, `updateTableDiscoveryPolicy`, `useGetTableDiscoveryPolicyVersion`, their query keys; `GlobListField` (unchanged).
- Produces:
  - `interface DiscoveryRuleDraft { key: string; id: string | null; outcome: "manage" | "unmanage"; namespaces: string[]; tables: string[] }` (an empty list means no condition on that attribute).
  - `interface DiscoveryPolicyDraft { version: number; description: string; noMatchOutcome: "manage" | "unmanage"; rules: DiscoveryRuleDraft[] }`.
  - `draftFromPolicy(policy: TableDiscoveryPolicyApiResponse): DiscoveryPolicyDraft`; `updateRequest(draft): UpdateTableDiscoveryPolicyApiRequest` (rules in draft order, a new rule without `id`, conditions `namespace` then `table`, only the non-empty ones, operator `glob`); `newRuleDraft(key: string): DiscoveryRuleDraft` (outcome `manage`, no globs); `movedRule(rules, rule, by: -1 | 1)`; `ruleHasCondition(rule): boolean`.
  - `DiscoveryRulesTable({ rules, readOnly, actions? })`: columns `#` (position), Outcome badge, Namespaces, Tables (globs as mono badges, `—` when none) and, unless `readOnly`, move up / move down / Edit / Delete; caption "Discovery rules in evaluation order".

- [ ] **Step 1: Failing tests and stories.**
  - `discoveryPolicyDraft.test.ts`: a policy round-trips draft → request unchanged; a new rule is sent without `id`; a rule with only table globs sends one `table` condition.
  - `DiscoveryRuleEditor`: Outcome select, Namespace globs, Table globs; with both empty the submit is disabled and the dialog says "A rule needs at least one namespace or table glob."; keyboard: Tab order, Escape closes and returns focus.
  - `DiscoveryPolicyPage`: header with the name, `Version N`, saved time and links to `v1` … `vN`; description `TextArea`; "When no rule matches" `Select`; the rules table with Add rule; Save / Discard enabled only when the draft differs; a 409 shows "Someone else changed this policy. Reload to see their version." with Reload; a 422 shows the detail; after a save "Saved. Discovering tables…". The default policy shows an information `Banner` with its fixed description and a read-only rules table, no Save. Deleting an unsaved rule needs no confirmation.
  - `DiscoveryPolicyVersionPage`: read-only description, no-match outcome and `DiscoveryRulesTable readOnly`; a non-numeric version shows "a version is a whole number"; 404 shows the API detail; breadcrumbs Discovery policies → name → `name vN`.
  - Stories for both pages: loaded, default, conflict, error, phone width.
- [ ] **Step 2: Run and watch them fail:** `npm --prefix src/data-platform/frontend test -- --run discoveryPolicyDraft DiscoveryRuleEditor DiscoveryRulesTable DiscoveryPolicyPage DiscoveryPolicyVersionPage`
- [ ] **Step 3: Implement.** Keep the draft-against-version pattern of today's `DiscoveryRulesPage` (a refetch never moves the draft's version; refetch in `onSettled`).
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`
- [ ] **Step 5: Commit** `feat(console): edit a discovery policy's rules and read its versions (KCL-71)`

### Task 11: Console: attach and detach a discovery policy, with condition hints

**Files:**
- Create: `components/DiscoveryPolicyAttachments.tsx`, `components/AttachDiscoveryPolicyDialog.tsx` (each + `.stories.tsx`, `.test.tsx`), `lib/discoveryRuleHints.ts` (+ `.test.ts`)
- Modify: `pages/DiscoveryPolicyPage.tsx` (an "Attached to" section under the rules; hints under each rule row), `components/DiscoveryRulesTable.tsx` (optional `hints` per rule key), `stories/lakehouseHandlers.ts`
- Test: the files above

**Interfaces:**
- Consumes: `useListTableDiscoveryPolicyAttachments`, `attachTableDiscoveryPolicy`, `detachTableDiscoveryPolicy`, `getListScannedCatalogsQueryKey`, `useListCatalogs` (catalog context), `targetPagePath` / `targetName` from `lib/policyPaths.ts`.
- Produces: `ruleHints(rule: DiscoveryRuleDraft, attachments: { type: string; path: string[] }[]): string[]` returning, once per rule: for any table attachment, "On a table this rule either always or never matches it."; for a namespace attachment when the rule has namespace globs, "Attached to namespace <path>: namespace globs only tell its child namespaces apart."

- [ ] **Step 1: Failing tests and stories.** The section lists each target (kind, linked name, an `Orphaned` neutral badge) with Detach (no confirmation, `aria-label="Detach from <name>"`); empty text "Not attached. Attach it to a catalog, namespace or table to apply it." Attach opens the dialog: Type (`Catalog` / `Namespace` / `Table`), Catalog (`Select` from `GET /v1/catalogs`), Namespace (dot-joined `TextField`, hidden for a catalog), Table (`TextField`, only for a table); the API's 403 / 404 detail shows inside the dialog and keeps it open. After an attach or detach, success or not, refetch this policy's attachments, the policy list and `/v1/scanned-catalogs`. Keyboard test for the dialog. `ruleHints` unit tests for both hints and for none.
- [ ] **Step 2: Run and watch them fail:** `npm --prefix src/data-platform/frontend test -- --run DiscoveryPolicyAttachments AttachDiscoveryPolicyDialog discoveryRuleHints DiscoveryPolicyPage`
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run and watch them pass**; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`
- [ ] **Step 5: Commit** `feat(console): attach and detach discovery policies from the policy page (KCL-71)`

### Task 12: Console: the table page reads the scanned catalogs; the rules page goes

**Files:**
- Delete: `pages/DiscoveryRulesPage.tsx` (+ stories, test), `lib/discoveryRuleDraft.ts`
- Modify: `pages/TablePage.tsx` (`useListScannedCatalogs` instead of `useListCoveredCatalogs`), `lib/tableMaintenanceState.ts` (reason `catalog-not-scanned`), `components/MaintenanceEmptyState.tsx` (+ test), `components/tabs/OverviewTab.tsx` (no `useGetTableDiscoveryRules`), `components/TableHeader.tsx` (comment), `stories/lakehouseHandlers.ts`, `stories/storyData.ts`, every page test that stubbed `/v1/discovery-rules*` (`CatalogPage`, `NamespacePage`, `GenericTablePage`, `ViewPage`, `TableListPage`, `TablePage`, `TablePage.mobile`)
- Test: the files above

**Interfaces:**
- Consumes: `useListScannedCatalogs`.
- Produces: `MaintenanceEmptyReason = "catalog-not-scanned" | "not-found" | "unmanaged" | "dropped"`; messages "no discovery policy in this catalog manages tables" and "the discovery policy that applies does not manage this table"; the not-found, unmanaged and not-scanned reasons link to Discovery policies (`/discovery-policies`).

- [ ] **Step 1: Failing tests:** a table in an unscanned catalog shows the not-scanned reason with the link; the Overview's "Discovery rule" row shows the managed table's `matched_rule_id` in `font-mono`, or "None: no rule matched, the policy manages the rest" when it is null; no request goes to `/v1/discovery-rules*` from any page (assert on the MSW call log in `TablePage.test.tsx`).
- [ ] **Step 2: Run and watch them fail:** `npm --prefix src/data-platform/frontend test -- --run TablePage MaintenanceEmptyState OverviewTab tableMaintenanceState`
- [ ] **Step 3: Implement**; `grep -rn "discovery-rules\|DiscoveryRules\|useListCoveredCatalogs" src/data-platform/frontend/src --include='*.ts*' | grep -v api/generated` prints only the redirect route.
- [ ] **Step 4: Run and watch them pass**; `npm --prefix src/data-platform/frontend run test:stories`, then `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=frontend`
- [ ] **Step 5: Commit** `feat(console): show why a table is not managed in terms of discovery policies (KCL-71)`

### Task 13: Remove the discovery rules aggregate and the configured catalog list

**Files:**
- Delete: `TM/application/domain/model/table_discovery_rules/`, `TM/application/port/inbound/table_discovery_rules/`, `TM/application/port/outbound/table_discovery_rules/`, `TM/application/service/table_discovery_rules/`, `TM/adapter/outbound/table_discovery_rules/`, `TM/adapter/inbound/web/table_discovery_rules/`, `tests/context/table_maintenance/fakes/in_memory_table_discovery_rules_repo.py` and every test directory named `table_discovery_rules`
- Modify: `TM/adapter/outbound/shared/sql/create_schema.py` (`AGGREGATE_SQL_PACKAGES` drops the rules package), `TM/adapter/inbound/web/register_routes.py`, `web_use_cases.py`, `TM/application/service/shared/translate_domain_errors.py` (drops `StaleDiscoveryRulesVersion`), `tests/architecture/test_aggregates.py`, `bootstrap/configs/catalog_settings.py` (drops `names` and its docstring sentence), `app_settings.py` docstring (example `GLAC_CATALOG__NAMES` goes), `bootstrap/container/{use_cases,repositories,build_use_cases,build_repositories,build_connected_use_cases,build_web_use_cases}.py`, `tests/bootstrap/**` that named rules or `catalog.names`, `tests/context/table_maintenance/adapter/inbound/web/policy_web_world.py`, `openapi.json` + client (the `discovery-rules` client module disappears)
- Test: `tests/architecture`, `tests/bootstrap`, the whole backend suite

**Interfaces:**
- Consumes: Tasks 7, 8 and 12 (nothing reads the rules any more; the console no longer imports the `discovery-rules` client).

- [ ] **Step 1: Write the failing test:** a route test `test_discovery_rules_routes_are_gone(client)`: `GET /v1/discovery-rules` and `GET /v1/discovery-rules/catalogs` answer 404; and `test_catalog_settings_have_no_names()`: `"names" not in CatalogSettings.model_fields`.
- [ ] **Step 2: Run and watch it fail:** `uv run --project src/data-platform/backend --directory src/data-platform/backend pytest tests -k "discovery_rules_routes_are_gone or catalog_settings_have_no_names" -v`
- [ ] **Step 3: Delete and rewire**; `grep -rn "discovery_rules\|DiscoveryRules\|ListCoveredCatalogs\|catalog\.names\|rules_version" src/data-platform/backend --include='*.py'` prints nothing; regenerate the client.
- [ ] **Step 4: Run** the whole backend suite, `lint-imports` and then `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all` (the client changed).
- [ ] **Step 5: Commit** `refactor(table-maintenance): remove the discovery rules list and the configured catalog names (KCL-71)`

### Task 14: Platform: chart, validation and the end-to-end check

**Files:**
- Modify: `platform/25-lakehouse-control-plane/chart/values.yaml` (drop `catalog.names`), `chart/templates/configmap.yaml` (drop `GLAC_CATALOG__NAMES`), `platform/25-lakehouse-control-plane/validate.sh`, `e2e.sh`, `README.md`

**Interfaces:**
- Consumes: the API of Tasks 5, 6 and 8.

- [ ] **Step 1: Write the failing checks in `validate.sh`:** `GET /v1/discovery-policies/default` answers 200 with `"is_default":true` and no rules; `GET /v1/discovery-rules` answers 404 (like the `/v1/policy-templates` check); `GET /v1/scanned-catalogs` lists the scanned catalogs, and the `table-discovery:catalog=` schedules listed by `temporal schedule list` in `deployment/temporal-admintools` are exactly those (no missing, no extra). The `GLAC_CATALOG__NAMES` block goes. Run `helm template platform/25-lakehouse-control-plane/chart | grep -c GLAC_CATALOG__NAMES` and expect `1` before the edit.
- [ ] **Step 2: Rewrite the e2e setup.** Replace "ensuring the discovery rule" with: create the policy `tm-e2e` if `GET /v1/discovery-policies/tm-e2e` is 404 (`no_match_outcome` `unmanage`, one rule `manage` on `{"attribute": "table", "operator": "glob", "values": ["tm_e2e_*"]}`), and after the `CREATE TABLE` statements attach it to `{"type": "namespace", "path": ["iceberg", "${SCHEMA}"]}` (a namespace must hold a table to be attached). `RULE_ID` is the policy's `rules[0].id`; `assert_prefixed_ids` also checks the policy's `dp-` id (attachment ids are not in the API). After the attach, wait until `table-discovery:catalog=iceberg` exists. At the end, detach and check the schedule is gone if no other policy in `iceberg` manages tables (read `GET /v1/scanned-catalogs` first and skip the check when `iceberg` stays scanned).
- [ ] **Step 3: Update `README.md`:** the settings paragraph (no catalog names; `GLAC_DISCOVERY_INTERVAL_SECONDS` 60 to 86400), the API table (the discovery-policies rows and `/scanned-catalogs` replace the discovery-rules row), the curl example (create, then attach), and the workflow-id table (`trigger=policy-changed:change={id}` beside `trigger=adhoc`; the schedule exists only while the catalog is scanned).
- [ ] **Step 4: Run** `helm template platform/25-lakehouse-control-plane/chart | grep -c GLAC_CATALOG__NAMES` → `0`; `bash -n platform/25-lakehouse-control-plane/validate.sh platform/25-lakehouse-control-plane/e2e.sh`; `uv run pre-commit run shared --all-files`; `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`.
- [ ] **Step 5: Commit** `feat(platform): validate discovery policies and drive the e2e through them (KCL-71)`

### Task 15: Docs

**Files:**
- Modify: `src/data-platform/backend/CLAUDE.md` (aggregate list: `catalog_discovery`, `table`, `table_discovery_policy`, `table_discovery_policy_attachment`, `table_maintenance_policy`, `table_maintenance_policy_attachment`, `table_maintenance_run`, `table_reconciliation`; the DTO example becomes `UpdateTableDiscoveryPolicyApiRequest` / `TableDiscoveryPolicyApiResponse` in `adapter/inbound/web/table_discovery_policy/dto.py`; one paragraph on discovery: nearest attachment, derived scanned catalogs, rescan and schedule sync after a change, `PolicyTarget` in `shared`), `src/data-platform/frontend/CLAUDE.md` (the `MaintenanceEmptyState` reasons, the Overview's discovery rule row, the discovery policy pages and that attach lives on the policy page until KCL-98), root `CLAUDE.md` (Project Vision aggregate list), `docs/adr/0005-bounded-contexts-and-context-map.md` (one "Updated 2026-11-20" line), `docs/adr/0011-prefixed-resource-ids.md` (`dp-` TableDiscoveryPolicyId, `da-` TableDiscoveryPolicyAttachmentId), `docs/agents/known-follow-ups.md`, `docs/agents/project-history.md`

- [ ] **Step 1: Write the follow-ups:** two concurrent changes can sync the schedules in the wrong order (the later sync may delete a schedule the other just needed) until the next change or worker start; a schedule sync or rescan that fails after a change is only logged; a catalog or namespace with no table cannot be attached (the table-reading gateway cannot list them); a renamed table's `matched_rule_id` may name a rule of a policy that no longer applies until the next scan.
- [ ] **Step 2: Write the history line:** `2026-11-20: KCL-71: discovery rules became versioned discovery policies (dp-, default dp-0…0 manages nothing), attached to catalogs, namespaces and tables (da-), nearest wins; the catalogs scanned follow the attachments and GLAC_CATALOG__NAMES is gone; console pages /discovery-policies.`
- [ ] **Step 3: Run** `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr scope=all`
- [ ] **Step 4: Commit** `docs: record discovery policies (KCL-71)`

### Task 16: Verify on a rebuilt cluster (controller)

- [ ] **Step 1:** `task offboard KUBE_CONTEXT=retail-lakehouse`, then `task onboard KUBE_CONTEXT=retail-lakehouse`; `task apps:validate KUBE_CONTEXT=retail-lakehouse` exits 0 (no discovery schedule exists yet, `GET /v1/scanned-catalogs` is `{"catalogs": []}`).
- [ ] **Step 2:** Through the API (port-forward or `kubectl exec deployment/table-maintenance-api --namespace lakehouse-control-plane --context retail-lakehouse`): create a policy managing `*` with no-match `unmanage`, attach it to a namespace of `iceberg` that holds tables. Within a minute `temporal schedule describe --schedule-id table-discovery:catalog=iceberg` succeeds in `deployment/temporal-admintools`, an ad hoc `trigger=policy-changed` run completes, and `GET /v1/tables?status=managed` lists that namespace's tables with `matched_rule_id` set.
- [ ] **Step 3:** Attach `default` to one of those tables: after its rescan that table is unmanaged and the others stay managed. Detach the namespace policy: every table of the namespace becomes unmanaged and the `iceberg` schedule is gone (`temporal schedule list` shows no `table-discovery:` schedule).
- [ ] **Step 4:** Attach to a catalog the credential cannot read (or a made-up one): 403 or 404 with the detail, nothing stored. Change the interval with `helm upgrade` setting `worker.discoveryIntervalSeconds=300` (reattach first), restart the worker (`kubectl rollout restart deployment/table-maintenance-worker --namespace lakehouse-control-plane --context retail-lakehouse`): the schedule's interval reads 5m.
- [ ] **Step 5:** In the console: the sidebar's Discovery policies, create a policy, add and reorder rules, save (version 2 appears, v1 readable), attach and detach from the page, the default is read-only, `/discovery-rules` redirects, a table in an unscanned catalog shows the not-scanned reason; check phone width.
- [ ] **Step 6:** If Trino is back (it is paused since 2026-11-19, `platform/CLAUDE.md`), run `platform/25-lakehouse-control-plane/e2e.sh` with `KUBE_CONTEXT=retail-lakehouse`; otherwise say so in the report. Then `task -d /Users/kcl/Projects/retail-lakehouse gates:pre-pr`; record the results on KCL-71 in a dated comment; push only when the user asks.
