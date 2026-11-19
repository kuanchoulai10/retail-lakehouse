# Prefixed Resource IDs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every resource id the table maintenance context generates says what it is (`mr-01h455vb4pex5vsknk084sn02q`), is checked for that shape wherever it enters, and maintenance policies get an id of their own so names are only for display and URLs.

**Architecture:** A stdlib-only `shared_kernel` package encodes a UUIDv7 as a 26-character Crockford base32 suffix (the TypeID suffix encoding). `base.EntityId` gains an optional class-level `PREFIX`: a prefixed id type refuses any other shape and can mint a new value. Domain and services mint ids with `XId.new()`; Temporal workflows (which cannot import `base` or Pydantic) mint them deterministically with `shared_kernel.prefixed_id_from_parts(prefix, workflow.now(), workflow.random())`.

**Tech Stack:** Python 3.14 (`uuid.uuid7`), Pydantic 2.12, SQLAlchemy, Temporal Python SDK, FastAPI, React console.

**Spec:** Linear KCL-73: description plus the comments of 2026-11-17 (format, prefix list) and 2026-11-19 (scope after the survey: all eight prefixes, `pa-`/`cc-` random with unique constraints, fixed `dp-`, `mp-` complete, no data migration).

## Global Constraints

- Format: `<prefix>-<suffix>`, suffix = 26 lowercase Crockford base32 characters of a UUIDv7 (alphabet `0123456789abcdefghjkmnpqrstvwxyz`, first character `0`–`7`), exactly the TypeID suffix encoding. Regex for a prefix `p`: `^p-[0-7][0-9a-hjkmnp-tv-z]{25}$`.
- Prefixes (table_maintenance only): `mp-` TableMaintenancePolicyId (new), `dp-` TableDiscoveryRulesId, `dr-` TableDiscoveryRuleId, `pa-` TableMaintenancePolicyAttachmentId, `mr-` TableMaintenanceRunId, `rc-` TableReconciliationId, `cr-` CompactionRoundId, `cc-` CompactionCandidateId.
- Unchanged ids: table_maintenance `TableId` (Iceberg table UUID), `CatalogDiscoveryId` (catalog name), every id in the catalog context (Polaris).
- Fixed ids: the global discovery rules `dp-00000000000000000000000000`; the default maintenance policy `mp-00000000000000000000000000`.
- No data migration: old rows are not converted; the cluster is rebuilt (offboard/onboard) after deploy. A stored id of the old shape is refused on read.
- REST paths and console URLs keep using policy names (`/v1/maintenance-policies/{name}`, `/policies/:name/versions/:version`). Every relation to a policy is by `mp-` id.
- Temporal activity names never change (`test_wire_names.py`). Workflow id shapes keep their wording (`table-maintenance:table=…:run=<mr-id>`, `table-reconciliation:table-uuid=…`); only the run id inside changes.
- Workflows mint ids only from `workflow.now()` and `workflow.random()` (determinism test forbids `uuid`, `random`, `time`, `secrets` in the workflows package).
- Backend rules: TDD, one object per file, `from __future__ import annotations`, run as `uv run --project src/data-platform/backend --directory src/data-platform/backend <cmd>`, every commit passes `pytest -q`, `ty check`, `ruff check .`, `lint-imports`; the console OpenAPI contract may change only where a task says so, and `task dev:generate-api` is re-run when it does.
- Tests: where a value does not matter use `XId.new()`; where a fixed value is needed use a valid literal of the new shape (module-level constant). Never weaken the format check for tests.

## Review Focus

1. A stale link or bookmark carrying an old UUID (`?run=<uuid>`, `/v1/table-maintenance-runs/<uuid>`) must answer 422 naming the expected shape, never 500. → Task 4 test `test_get_run_with_an_old_uuid_is_422`.
2. A replayed workflow or a retried activity must reuse the same run, reconciliation and round id. → Task 4 `test_run_and_reconciliation_ids_survive_replay`, Task 5 `test_round_id_is_stable_across_activity_retries`.
3. Two attaches to the same target at once leave exactly one attachment. → Task 7 `test_concurrent_attach_to_one_target_keeps_one`.
4. A partition observed again keeps its one candidate row (same `cc-` id), not a second one. → Task 6 `test_reobserved_partition_keeps_its_candidate_id`.
5. Spark application names stay unique and within Kubernetes limits for runs started in the same millisecond. → Task 4 `test_spark_application_name_differs_for_runs_in_one_millisecond`.

---

### Task 1: Shared kernel encoder and ADR

**Files:**
- Create: `src/data-platform/backend/shared_kernel/__init__.py`, `shared_kernel/prefixed_id_from_parts.py`, `shared_kernel/new_prefixed_id.py`, `shared_kernel/prefixed_id_pattern.py`
- Modify: `src/data-platform/backend/.importlinter` (root package `shared_kernel`; new contract `shared-kernel-stdlib-only`: forbids `base`, `bootstrap`, `context`, `pydantic`, `temporalio`, `sqlalchemy`, `fastapi`), `pyproject.toml` if packages are listed
- Create: `docs/adr/0011-prefixed-resource-ids.md`; Modify: root `CLAUDE.md` ADR row, `src/data-platform/backend/CLAUDE.md` (DDD base types / ids section)
- Test: `tests/shared_kernel/test_prefixed_id.py`

**Interfaces:**
- Produces: `prefixed_id_from_parts(prefix: str, unix_ms: int, random_bits: int) -> str` (builds the UUIDv7 integer: 48-bit ms, version 7, 12 + 62 random bits from the low 74 bits of `random_bits`, variant `10`; encodes it); `new_prefixed_id(prefix: str) -> str` (uses `uuid.uuid7()`); `prefixed_id_pattern(prefix: str) -> re.Pattern[str]`. Prefix must match `^[a-z]{2,8}$`, else `ValueError`.

- [ ] Step 1: failing tests
  - `test_encodes_the_typeid_spec_vector`: the UUID `0188bac7-4afa-78aa-bc3b-bd1eef28d881` encodes to suffix `01h2xcejqtf2nbrexx3vqjhp41` (expose a private `_encode(int) -> str` or test via `prefixed_id_from_parts` with the vector's ms and random bits).
  - `test_ids_sort_by_time`: ids from `unix_ms=1` and `unix_ms=2` compare in that order as strings.
  - `test_suffix_shape`: `new_prefixed_id("mr")` matches `prefixed_id_pattern("mr")`, length 29.
  - `test_same_parts_same_id` and `test_different_random_bits_differ`.
  - `test_refuses_bad_prefix`: `"MR"`, `"m"`, `"mr-"` raise `ValueError`.
- [ ] Step 2: run, watch fail. Step 3: implement. Step 4: pass; `lint-imports` shows the new contract kept.
- [ ] Step 5: ADR 0011 (context: KCL-73; decision: format, prefix list, unchanged ids, shared kernel and why — workflows cannot import `base`; consequences: no migration, names for URLs only, `pa-`/`cc-` uniqueness moves to constraints). Commit `feat(backend): add shared kernel prefixed id encoder (ADR 0011)`.

### Task 2: `EntityId.PREFIX`

**Files:**
- Modify: `src/data-platform/backend/base/entity_id.py`
- Test: `tests/base/test_entity_id.py`; Create: `tests/architecture/test_prefixed_ids.py`

**Interfaces:**
- Consumes: Task 1.
- Produces: `EntityId.PREFIX: ClassVar[str | None] = None`; when set, construction (any path, incl. `model_validate`) refuses a value not matching `prefixed_id_pattern(PREFIX)` with `InvariantViolation` whose message names the class and the expected shape (`"TableMaintenanceRunId must look like mr-<26 base32 characters>"`); `XId.new() -> XId` (raises `TypeError` when `PREFIX` is None).
- Produces (architecture test): `EXPECTED_PREFIXES: dict[str, str]` in `test_prefixed_ids.py` mapping class name → prefix, plus `UNPREFIXED: frozenset[str]` = `{"TableId", "CatalogDiscoveryId"}` for table_maintenance; the test walks every `EntityId` subclass under `context/table_maintenance` and checks it is in exactly one of the two, that `PREFIX` matches, and that prefixes are unique project-wide. Start with `EXPECTED_PREFIXES` empty and a `PENDING` set naming the eight targets (and `TableMaintenancePolicyId` as not-yet-existing); each later task moves its rows from `PENDING` to `EXPECTED_PREFIXES`; Task 8 empties `PENDING`.

- [ ] Steps: failing tests (`test_prefixed_id_refuses_a_uuid`, `test_prefixed_id_accepts_its_shape`, `test_new_mints_a_valid_id`, `test_unprefixed_id_accepts_any_string`, `test_new_without_prefix_is_type_error`, architecture test with fake subclasses) → implement → pass → commit `feat(base): let an EntityId declare its prefix`.

### Task 3: Discovery rules `dp-` and rules `dr-`

**Files:** `M/table_discovery_rules/table_discovery_rules_id.py`, `table_discovery_rule_id.py` (`M/` = `context/table_maintenance/application/domain/model/`); `application/service/table_discovery_rules/replace_table_discovery_rules.py` (default `new_id` → `TableDiscoveryRuleId.new().value`); `adapter/outbound/table_discovery_rules/sql/table_discovery_rules_sql_repo.py` (`"global"` literal → the constant); tests that build these ids; console fixtures/stories with rule ids; `tests/architecture/test_prefixed_ids.py` rows.

**Interfaces:** `GLOBAL_TABLE_DISCOVERY_RULES_ID = TableDiscoveryRulesId("dp-00000000000000000000000000")`.

- [ ] Tests first: `test_rule_ids_minted_by_replace_have_the_dr_prefix`; `test_replace_refuses_a_rule_id_of_another_shape` (a request id `"r-1"` → 422 through the web route); `test_global_rules_id_is_the_fixed_dp_id`. Update existing literals (`"r-1"` etc.) to valid constants. Commit `feat(table-maintenance): prefix discovery rule ids`.

### Task 4: Runs `mr-` and reconciliations `rc-`

**Files:** `M/table_maintenance_run/table_maintenance_run_id.py`, `M/table_reconciliation/table_reconciliation_id.py`; `adapter/hybrid/temporal/inbound/workflows/table_reconciliation_workflow.py:426-427` (mint with `prefixed_id_from_parts("rc"|"mr", int(workflow.now().timestamp()*1000), workflow.random().getrandbits(74))`); `adapter/outbound/table_maintenance_run/k8s/spark_application_name.py` (use the run id's 26-character suffix, not its first 20 alphanumerics: `tm-<code>-<suffix>-a<attempt>`); console `components/tabs/ReconciliationsTab.tsx:94` (show the whole run id, monospace, no slicing); `platform/25-lakehouse-control-plane/e2e.sh` if any check assumes the old shape; `docs/adr/0002-entity-workflow-per-table.md` example ids; tests and console fixtures.

- [ ] Tests first:
  - `test_run_and_reconciliation_ids_survive_replay` (Temporal replayer or a workflow-environment test that the ids passed to the plan and record activities are the same on replay, and have the `mr-`/`rc-` shape).
  - `test_get_run_with_an_old_uuid_is_422` (`GET /v1/table-maintenance-runs/3f2504e0-4f89-11d3-9a0c-0305e82c3301` → 422, body names the shape) and the same for the callback route.
  - `test_spark_application_name_differs_for_runs_in_one_millisecond` (two run ids with the same ms, different random bits → different names; every name ≤ 63 characters and a valid DNS-1123 label).
  - Console unit test: the reconciliations tab shows the full run id.
- [ ] Commit `feat(table-maintenance): prefix run and reconciliation ids`.

### Task 5: Compaction rounds `cr-`

**Files:** `M/compaction_round/compaction_round_id.py`; `adapter/hybrid/temporal/inbound/workflows/compaction_round_workflow.py:54` (mint `cr-` once at workflow start from `workflow.now()`/`workflow.random()`; the round workflow has one run per workflow id — no retry policy on the schedule action, no continue-as-new — so the id is stable; add a test pinning that the schedule action sets no retry policy); console `pages/CompactionRoundsPage.tsx:165` label "Workflow id" → "Round id"; `src/data-platform/backend/CLAUDE.md:67` and `platform/25-lakehouse-control-plane/README.md:130` (round id is minted by the workflow, no longer the workflow id); fixtures with `compaction-rounds-…` round ids in backend and console tests and stories.

- [ ] Tests first: `test_round_id_is_stable_across_activity_retries` (the schedule activity retried with the same payload finds its saved record and grants, using the `cr-` id); `test_round_workflow_passes_a_cr_id`; `test_schedule_action_has_no_retry_policy`. Commit `feat(table-maintenance): prefix compaction round ids`.

### Task 6: Compaction candidates `cc-`

**Files:** `M/compaction_candidate/compaction_candidate_id.py` (drop `for_partition`; `PREFIX = "cc"`), `M/compaction_candidate/compaction_candidate.py:135` (`CompactionCandidateId.new()`); every caller that recomputed an id from a partition switches to looking up by `(table_uuid, partition_key)` through the repository (add `get_for_partitions(table_uuid, keys)` or reuse an existing finder); `adapter/outbound/compaction_candidate/sql/*` (unique constraint `(table_uuid, partition_key)` stays and is now the identity guarantee; an insert colliding on it still becomes `StaleCompactionCandidate`).

- [ ] Tests first: `test_reobserved_partition_keeps_its_candidate_id` (observe, save, observe the same partition again → one row, same id); `test_new_candidate_gets_a_cc_id`; `test_concurrent_first_observation_of_one_partition_is_stale_for_the_loser` (SQL repo, two saves of fresh candidates for one partition). Commit `feat(table-maintenance): prefix compaction candidate ids`.

### Task 7: Policy attachments `pa-`

**Files:** `M/table_maintenance_policy_attachment/table_maintenance_policy_attachment_id.py` (`PREFIX = "pa"`), `policy_target.py` (the derived string becomes `PolicyTarget.key() -> str`, no longer an id), `table_maintenance_policy_attachment.py` (id minted on attach); services `attach_table_maintenance_policy.py`, `detach_table_maintenance_policy.py`, `resolve_applicable_table_maintenance_policy.py`, `notify_policy_change.py` (find attachments by target key); outbound port + SQL repo: new column `target_key` String NOT NULL with a unique index, finders `get_by_target(target)` / `get_many_by_targets(targets)`; table definition with `server_default` not needed (no migration — fresh schema).

- [ ] Tests first: `test_attach_twice_to_one_target_replaces_not_duplicates`; `test_concurrent_attach_to_one_target_keeps_one` (SQL repo: two inserts for one `target_key`, the second refused and surfaced as the existing domain conflict or a replace — whichever the attach service does today for a second attach, keep that behaviour); `test_attachment_id_has_the_pa_prefix`; resolve still picks table > namespace > catalog. Commit `feat(table-maintenance): prefix policy attachment ids`.

### Task 8: Maintenance policies `mp-` (complete)

**Files:** Create `M/table_maintenance_policy/table_maintenance_policy_id.py` (`PREFIX = "mp"`), `M/table_maintenance_policy/default_policy_id.py` (`DEFAULT_POLICY_ID = TableMaintenancePolicyId("mp-00000000000000000000000000")`); `TableMaintenancePolicy.id` becomes `TableMaintenancePolicyId`, `name: TableMaintenancePolicyName` an attribute (unique); default detection by `DEFAULT_POLICY_ID`; `bootstrap/container/run_migrations.py` seeds the default with that id.
Relations move from name to id:
- SQL: `table_maintenance_policies` PK `id`, `name` unique; `table_maintenance_policy_versions` PK `(policy_id, version)` FK → policies.id; `table_maintenance_policy_attachments.policy_id` FK; `table_reconciliations.policy_id`; `tables.operation_states_json` attention mark `{"policy": {"id", "version", "target"}}` (`M/table/applied_policy_ref.py`).
- Temporal plan payload and record input: `policy_id` replaces `policy_name` (`plan_table_maintenance.py`, `table_maintenance_workflow.py` `_PLANNED_POLICY_KEYS`, `table_reconciliation_workflow.py:526`, `record_table_maintenance_operation_result` input and service).
- Ports: inputs that name a policy by URL keep `name`; outputs that point at a policy carry `policy_id` and `policy_name` (current name, read through the repository), so the console can keep linking by name.
- REST: paths unchanged; responses add `id` to a policy, and `policy_id` beside every `policy_name` (attachments, reconciliations, applicable policy, table attention). Regenerate `openapi.json` and the console client (`task dev:generate-api`); console code keeps linking by name and needs only type updates; e2e works by name and keeps working.
- `tests/architecture/test_prefixed_ids.py`: `PENDING` empty.

- [ ] Tests first: `test_policy_gets_an_mp_id_on_create`; `test_default_policy_has_the_fixed_id`; `test_attachment_points_at_the_policy_id`; `test_reconciliation_record_points_at_the_policy_id_and_lists_its_name`; `test_plan_payload_carries_policy_id` (golden Temporal payload updated deliberately, the only intended payload change); `test_policy_routes_still_use_names`. Commit(s) `feat(table-maintenance): give maintenance policies an mp- id`; split into green commits (domain+SQL, relations, API) as useful.

### Task 9 (controller): deploy, rebuild, verify

1. `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/bootstrap.sh`, then `task offboard` / `task onboard KUBE_CONTEXT=retail-lakehouse` (old rows have the old shape and would be refused), then `KUBE_CONTEXT=retail-lakehouse bash platform/25-lakehouse-control-plane/e2e.sh`.
2. Spot-check through the API and Temporal UI that run, reconciliation, round, rule and policy ids carry their prefixes and Spark application names use the run suffix.
3. `docs/agents/project-history.md` line; `docs/agents/known-follow-ups.md` for anything deferred; Linear KCL-73 comment and Done.
