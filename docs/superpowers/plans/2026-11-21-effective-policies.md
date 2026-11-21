# Effective Policies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The table, namespace and catalog pages show which maintenance policy and which discovery policy apply there, which version and from which level, and let the user attach, replace or detach either kind there; both kinds of attachment share one API shape.

**Architecture:** One application service walks both attachment repos with the shared `candidate_policy_targets` / `enclosing_policy_targets` and `nearest_attached`, and answers one entry per kind. Maintenance attachments take the discovery attachments' shape (`/attachments`, detach by the `pa-` id). The console replaces `ApplicablePolicyPanel` with one panel for both kinds. The two `applicable-policy` routes go; the internal `ResolveApplicableTableMaintenancePolicy` use case stays, because planning and recording use it.

**Tech Stack:** FastAPI + pydantic DTOs, SQLAlchemy repos, React + TanStack Query + orval client, MSW stories, vitest.

**Spec:** Linear KCL-98 (description, 完成條件) and `docs/adr/0012-policies-on-the-catalog-hierarchy.md` ("Aggregates and API", and the 2026-11-21 KCL-71 note). Code facts: `/Users/kcl/.claude/jobs/ffac9ee8/tmp/kcl98/facts.md` (read from 4bbe9001).

## Global Constraints

- Backend paths: `TM` = `src/data-platform/backend/context/table_maintenance`, `TT` = `src/data-platform/backend/tests/context/table_maintenance`, `FE` = `src/data-platform/frontend/src`.
- Project rules bind: one object per file, `from __future__ import annotations`, ABC, StrEnum, ports pydantic-free (import-linter), inbound-port dirs equal service dirs (`tests/architecture/test_aggregate_axis.py`).
- A route change regenerates the client with `task dev:generate-api`; the pre-pr `contract-test-console-api` check fails until `openapi.json` and `FE/api/generated` are committed (ruling R1 of KCL-71 applies: commit when only that check fails, then re-run the full gate).
- Every commit passes `task gates:pre-pr scope=all` (or the side it touches). Commit subjects are conventional, at most 100 characters, and end `(KCL-98)`.
- Console: design-system components only, no hard-coded colours, sentence case, keyboard operable, stories with play tests including a `Keyboard` and a `Phone` story for each new component.
- Copy, exact:
  - Panel title: `Policies`.
  - Row labels: `Maintenance`, `Discovery`.
  - Origin: `Attached here`, `From namespace <name>`, `From catalog <name>`, `Platform default`.
  - Buttons: `Attach policy` (nothing attached here), `Replace policy` (something attached here), `Detach`. Their accessible names add the kind: `Attach maintenance policy`, `Replace discovery policy`, `Detach maintenance policy`.
- An attachment always means the policy's latest version (ADR 0012), so `version` in an answer is the policy's current version.

## Rulings made while planning

- **P1, two read routes, not one.** ADR 0012 lists only `/v1/tables/{table_uuid}/effective-policies`, but the catalog and namespace pages and an unrecorded table need an answer by location, which only the old `GET /v1/applicable-policy?catalog&namespace&table` gave. So `GET /v1/effective-policies?catalog=&namespace=&table=` answers by location (namespace dot-joined, as the old route took it), and the uuid route answers for a table maintenance has a record of. Task 5 adds a dated note to ADR 0012 saying so.
- **P2, one entry per kind, a list.** The answer is `{"policies": [maintenance entry, discovery entry]}` in that order, so a third kind adds an entry. Each entry is a discriminated object on `kind`. The maintenance entry carries `dry_run`, so the panel keeps its dry-run badge without a second request. The discovery entry carries `no_match_outcome`.
- **P3, the entry carries the attachment id.** `attachment_id` is the `pa-` / `da-` id when the policy is attached at some level, and `null` for the platform default. The panel detaches by it.
- **P4, maintenance list takes a required policy name**, like discovery. If a caller needs all attachments it reads the repo.
- **P5, the effective-policies use case lives in the `table` aggregate package** (`port/inbound/table/get_effective_policies/`, `service/table/get_effective_policies.py`), because it answers "what applies to a table or a place in the catalog" and the axis test allows no new top-level package. The candidate walk shared with `ResolveApplicableTableMaintenancePolicyService` moves into one helper in `service/shared/` so the two cannot drift.
- **P6, a missing place is 404.** By location, a catalog, namespace or table that does not exist in the catalog is 404 (`CatalogNotFoundError`/`NotFoundError`), and a catalog the platform cannot read is 403, as attach already answers. By uuid, a table maintenance has no record of is 404.

## Review Focus

1. A table attached directly and also covered by a namespace attachment: the table's attachment wins for that kind only; the other kind still shows its own level. (Task 1 test.)
2. A table maintenance has no record of, asked by location: both kinds still answer, and a table attachment made by uuid is found. (Task 1 test.)
3. Detaching from the panel the policy attached at a parent level is not offered: `Detach` shows only when the entry's target is this page's target. (Task 3 test.)
4. Attaching a discovery policy from a namespace page also refreshes the scanned-catalog state and the discovery policy list counts, and attaching a maintenance policy refreshes the maintenance policy list counts. (Task 3 test.)
5. An old client or script still calling `/mappings` or `applicable-policy` gets 404, not a silent success. (Task 4 test.)

---

### Task 1: The effective policies of a table or a place in the catalog (backend)

**Files:**
- Create: `TM/application/port/inbound/table/get_effective_policies/` (`use_case.py`, `input.py`, `output.py`, `__init__.py`), `TM/application/service/table/get_effective_policies.py`, `TM/application/service/shared/policy_candidates.py`.
- Modify: `TM/application/port/inbound/table/__init__.py`, `TM/application/service/table/__init__.py`, `TM/application/service/shared/__init__.py`, `TM/application/service/table_maintenance_policy_attachment/resolve_applicable_table_maintenance_policy.py` (use the shared helper), `bootstrap/container/use_cases.py`, `bootstrap/container/build_use_cases.py`, `TM/adapter/inbound/web/shared/web_use_cases.py`, `TM/adapter/inbound/web/register_routes.py`.
- Create (web): `TM/adapter/inbound/web/table/effective_policies_router.py` (no prefix, tag `tables`), DTOs in `TM/adapter/inbound/web/table/effective_policies_dto.py`.
- Test: `TT/application/service/table/test_get_effective_policies.py`, `TT/application/service/shared/test_policy_candidates.py`, `TT/adapter/inbound/web/table/test_effective_policies_routes.py`; extend `TT/adapter/inbound/web/policy_web_world.py` or add a world that holds both kinds of repos.

**Interfaces:**
- Produces:
  - `policy_candidates(gateway, tables_repo, *, catalog: str | None, namespace: str | None, table: str | None, table_uuid: str | None) -> tuple[PolicyTarget, ...]`. Same rules as today's `_candidates` in the resolver: uuid only → `tables_repo.get` (NotFoundError if no record); catalog only or catalog + namespace → `enclosing_policy_targets`; catalog + namespace + table → the uuid given, else `gateway.load_table` (NotFoundError if absent) → `candidate_policy_targets`; neither catalog nor uuid → `ValidationError("name a catalog or a table uuid")`. By location it first checks the catalog and namespace exist (P6).
  - `GetEffectivePoliciesUseCaseInput{catalog: str | None = None, namespace: str | None = None, table: str | None = None, table_uuid: str | None = None}`.
  - `GetEffectivePoliciesUseCaseOutput{maintenance: MaintenanceEntry, discovery: DiscoveryEntry}` with nested frozen dataclasses: `MaintenanceEntry{policy_id, policy_name, version, description, dry_run: bool, target: dict | None, attachment_id: str | None}`, `DiscoveryEntry{policy_id, policy_name, version, description, no_match_outcome: str, target: dict | None, attachment_id: str | None}`. `target` uses the resolver's shape `{"type", "path": list, ["table_uuid"]}`.
  - `GetEffectivePoliciesService(maintenance_policies_repo, maintenance_attachments_repo, discovery_policies_repo, discovery_attachments_repo, gateway, tables_repo)`; no attachment → the default policy read from its repo (`DEFAULT_POLICY_ID`, `DEFAULT_DISCOVERY_POLICY_ID`).
  - Routes: `GET /v1/tables/{table_uuid}/effective-policies` and `GET /v1/effective-policies?catalog=&namespace=&table=` → `EffectivePoliciesApiResponse{policies: list[Annotated[MaintenanceEffectivePolicyApiResponse | DiscoveryEffectivePolicyApiResponse, Field(discriminator="kind")]]}`; each entry `{kind: Literal["maintenance"] | Literal["discovery"], policy_id, policy_name, version, description, target: PolicyTargetApiResponse | None, attachment_id: str | None}` plus `dry_run: bool` / `no_match_outcome: Literal["manage", "unmanage"]`. Operation ids `get_table_effective_policies`, `get_effective_policies`.

- [ ] **Step 1: Write the failing tests.** Service tests on fakes, each asserting both entries:
  - `test_a_table_with_nothing_attached_gets_both_platform_defaults` (targets `None`, attachment ids `None`, names `default`).
  - `test_each_kind_takes_its_own_nearest_attachment` — maintenance `gold` on the table, discovery `sales-tables` on namespace `sales`: maintenance target type `table` with its `pa-` id, discovery target `namespace` `["prod","sales"]` with its `da-` id.
  - `test_the_version_is_the_policys_latest` — update the attached policy, the answer's version moves.
  - `test_a_table_unknown_to_maintenance_is_answered_by_location` — not in the tables repo, attached by uuid: both kinds answer and the table attachment is found.
  - `test_a_namespace_or_catalog_is_answered_by_location`.
  - `test_by_uuid_a_table_without_a_record_is_not_found`, `test_by_location_a_missing_table_namespace_or_catalog_is_not_found`, `test_a_catalog_the_platform_cannot_read_is_refused`.
  - `policy_candidates` tests for each input shape and the `ValidationError`.
  - Route tests: both routes answer 200 with the list in order `["maintenance", "discovery"]` and the discriminated fields; 404 and 403 as above; 422 when neither catalog nor uuid.
- [ ] **Step 2: Run them and watch them fail** (`uv run --project src/data-platform/backend --directory src/data-platform/backend pytest <files> -v`).
- [ ] **Step 3: Implement.** Move the resolver's candidate walk into `policy_candidates` and call it from the resolver; its existing tests must pass unchanged.
- [ ] **Step 4: Run them and watch them pass**, then the whole backend suite.
- [ ] **Step 5: Regenerate the client** (`task dev:generate-api`), gate, commit `feat(table-maintenance): answer the effective maintenance and discovery policy of a table or place (KCL-98)`.

### Task 2: Maintenance attachments take the discovery attachments' shape (backend + call sites)

**Files:**
- Modify: the maintenance attachment ports and services under `TM/application/port/inbound/table_maintenance_policy_attachment/` and `TM/application/service/table_maintenance_policy_attachment/` (attach output gains `id`; list input `policy_name: str` required, items gain `id`; detach input becomes `{policy_name: str, attachment_id: str}`), the router and `dto.py` in `TM/adapter/inbound/web/table_maintenance_policy_attachment/`, `TM/adapter/inbound/web/shared/dto.py` and `__init__.py` (remove `DetachPolicyTargetApiRequest`).
- Modify (console call sites only, behaviour unchanged): `FE/components/PolicyAttachments.tsx`, `FE/components/AttachPolicyDialog.tsx` and its stories, `FE/components/ApplicablePolicyPanel.tsx` (detach by id: until Task 3 replaces this panel, read the id by listing the attached policy's attachments and matching the target), `FE/pages/PoliciesPage.tsx`, `FE/stories/lakehouseHandlers.ts`, `FE/stories/storyData.ts` (`POLICY_MAPPINGS` → `POLICY_ATTACHMENTS` with `pa-` ids), and the tests that name the old URLs (`PoliciesPage.test.tsx`, `TablePage.test.tsx`, `ApplicablePolicyPanel.test.tsx`, `PoliciesPage.stories.tsx`, `AttachPolicyDialog.stories.tsx`).
- Test: `TT/adapter/inbound/web/table_maintenance_policy_attachment/test_attachment_routes.py`, `TT/application/service/table_maintenance_policy_attachment/test_attachment_services.py`, `TT/adapter/inbound/web/policy_web_world.py` (`attach` PUTs `/attachments`; add `detach(name, attachment_id)`).

**Interfaces:**
- Produces, mirroring `TM/adapter/inbound/web/table_discovery_policy_attachment/router.py` exactly:
  - `GET /v1/maintenance-policies/{name}/attachments` → `TableMaintenancePolicyAttachmentsApiResponse{attachments: list[ListedTableMaintenancePolicyAttachmentApiResponse{id, target, policy_id, policy_name, attached_at, orphaned}]}`; 404 unknown policy. Operation id `list_table_maintenance_policy_attachments`.
  - `PUT /v1/maintenance-policies/{name}/attachments` with `AttachTableMaintenancePolicyApiRequest{target: PolicyTargetApiRequest}` → `TableMaintenancePolicyAttachmentApiResponse{id, target, policy_id, policy_name, attached_at}`; re-attaching the same target keeps the id; 403, 404, 422 as today.
  - `DELETE /v1/maintenance-policies/{name}/attachments/{attachment_id}` → 204; 404 unknown policy, unknown id or another policy's id; 422 malformed id. It does not read the catalog, so an orphaned attachment detaches. It still wakes the affected tables through `notify_policy_change`.
  - The `/mappings` routes are gone.
- Consumes from Task 1: nothing.

- [ ] **Step 1: Write the failing tests** — the discovery attachment route tests' counterparts: `test_put_attachment_answers_the_attachment` (id matches `prefixed_id_pattern("pa")`), `test_put_attachment_twice_keeps_the_id`, `test_get_attachments_marks_orphans` (with ids), `test_delete_attachment_answers_204_and_wakes_the_table`, `test_delete_an_orphaned_attachment_by_id`, `test_delete_with_a_malformed_id_is_422`, `test_delete_of_another_policys_attachment_is_404`, `test_mappings_routes_are_gone` (GET, PUT and DELETE on `/mappings` → 404 or 405). Service tests for detach by id, including that a detach of another policy's id changes nothing.
- [ ] **Step 2: Run them and watch them fail.**
- [ ] **Step 3: Implement**, then regenerate the client and update the console call sites so the console tests and stories pass unchanged in what they assert about the screen.
- [ ] **Step 4: Run backend, console unit and story tests.**
- [ ] **Step 5: Gate and commit** `refactor(table-maintenance): give maintenance attachments the discovery attachments' shape (KCL-98)`.

### Task 3: One policies panel for both kinds on the table, namespace and catalog pages (console)

**Files:**
- Create: `FE/components/EffectivePoliciesPanel.tsx` (+ `.test.tsx`, `.stories.tsx`), `FE/api/invalidateEffectivePolicies.ts` (+ test), `FE/lib/effectivePolicyOrigin.ts` (+ test).
- Modify: `FE/components/AttachPolicyDialog.tsx` gains `kind: "maintenance" | "discovery"` (lists that kind's policies, attaches through that kind's route, refreshes through `invalidateEffectivePolicies` plus that kind's invalidator), its stories; `FE/api/invalidatePolicyAttachments.ts` and `FE/api/invalidateDiscoveryPolicyAttachments.ts` also refresh effective policies; `FE/components/tabs/OverviewTab.tsx`, `FE/pages/CatalogPage.tsx`, `FE/pages/NamespacePage.tsx` and their tests and stories; `FE/stories/lakehouseHandlers.ts`, `FE/stories/storyData.ts` (an `effectivePolicies(catalog, namespace, table?)` fixture consistent with `POLICY_ATTACHMENTS`, `DISCOVERY_POLICY_ATTACHMENTS`).
- Delete: `FE/components/ApplicablePolicyPanel.tsx`, its test and stories.

**Interfaces:**
- Consumes from Task 1: `getTableEffectivePolicies` / `getEffectivePolicies` and their query options, `EffectivePoliciesApiResponse`, the two entry models. From Task 2: `detachTableMaintenancePolicy(name, attachmentId)`; existing `detachTableDiscoveryPolicy(name, attachmentId)`.
- Produces: `EffectivePoliciesPanel({ scope }: { scope: PolicyScope })`. A recorded table asks by uuid; anything else asks by location, as `ApplicablePolicyPanel` did. One row per entry, in the API's order: the label, the policy name linked to its version page (`policyVersionPath` / `discoveryPolicyVersionPath`) with `vN`, the origin text from `effectivePolicyOrigin(scope, entry)`, a `Dry run` badge on a maintenance entry with `dry_run`, and the buttons. `Detach` only when the entry is attached here (the same rule as today's `attachedHere`, table targets compared by uuid).
- `invalidateEffectivePolicies(queryClient): Promise<void[]>` refreshes every effective-policies query (both routes, by URL predicate, as `invalidateDiscoveryPolicyAttachments` does).

- [ ] **Step 1: Write the failing tests.**
  - `effectivePolicyOrigin` for each level and for a table attachment compared by uuid across a rename.
  - Panel: two rows in order; the origin text for each; `Detach` shown only for the kind attached here (Review Focus 3); detach sends `DELETE …/attachments/<id>` for that kind; attach and replace open the dialog for that kind with the current policy excluded; a failed read shows the API's detail with both rows absent; a failed detach shows the error and keeps focus on that `Detach`; after attach or detach the effective policies, that kind's attachment list and policy list (and scanned catalogs for discovery) are refetched (Review Focus 4); the whole flow by keyboard.
  - Pages: Overview, catalog and namespace pages render the panel with the right scope and request; an unrecorded table asks by location.
- [ ] **Step 2: Run them and watch them fail.**
- [ ] **Step 3: Implement**, then delete `ApplicablePolicyPanel`.
- [ ] **Step 4: Run console unit and story tests.**
- [ ] **Step 5: Gate and commit** `feat(console): show and change both kinds of policy where they apply (KCL-98)`.

### Task 4: Remove the applicable-policy routes

**Files:**
- Modify: `TM/adapter/inbound/web/table_maintenance_policy_attachment/router.py` and `dto.py` (remove both `applicable-policy` routes and `ApplicableTableMaintenancePolicyApiResponse`), `TM/adapter/inbound/web/shared/web_use_cases.py` (drop the resolver if no web route uses it any more; it stays in `bootstrap/container/use_cases.py` for planning), the regenerated client, and any console leftovers (`lakehouseHandlers.ts` imports, `storyData.ts` `applicablePolicy`).
- Test: `TT/adapter/inbound/web/table_maintenance_policy_attachment/test_applicable_policy_routes_are_gone.py`; delete the four `test_*applicable_policy*` route tests (their behaviour is covered by Task 1).

- [ ] **Step 1: Write the failing test** `test_applicable_policy_routes_are_gone`: `GET /v1/tables/u-1/applicable-policy` and `GET /v1/applicable-policy?catalog=prod` → 404 (Review Focus 5).
- [ ] **Step 2: Watch it fail; implement; regenerate; run backend and console tests; `git grep -n "applicable-policy\|ApplicablePolicy\|getGetApplicable\|mappings"` in `src/` finds only the internal resolver use case and unrelated words.**
- [ ] **Step 3: Gate and commit** `refactor(table-maintenance): remove the applicable-policy routes (KCL-98)`.

### Task 5: e2e and docs

**Files:**
- Modify: `platform/25-lakehouse-control-plane/e2e.sh` (`attach_policy` PUTs `/attachments` and keeps the returned `pa-` id; `assert_applicable_policy` becomes `assert_effective_policies`, reading `GET /v1/tables/{uuid}/effective-policies` and checking the maintenance entry names the table's policy with target type `table` and the discovery entry names `tm-e2e` from namespace `iceberg.e2e`; `assert_prefixed_ids` also checks the `pa-` ids), `platform/25-lakehouse-control-plane/README.md` (route table lines, e2e step text, the manual cleanup `DELETE …/attachments/<pa-id>`), `docs/adr/0012-policies-on-the-catalog-hierarchy.md` (dated 2026-11-21 KCL-98 note for P1–P3), `src/data-platform/frontend/CLAUDE.md` (the panel, the dialog's `kind`, discovery attach now also on target pages, `invalidateEffectivePolicies`), `src/data-platform/backend/CLAUDE.md` (effective policies, maintenance attachments by id), `docs/agents/project-history.md` (one line), `docs/agents/known-follow-ups.md` (only what this work defers).
- [ ] **Step 1:** Edit; `bash -n` and shellcheck on `e2e.sh`.
- [ ] **Step 2:** `git grep -n "mappings\|applicable-policy"` outside `docs/superpowers/` and dated history lines finds nothing current.
- [ ] **Step 3: Gate and commit** `docs(table-maintenance): describe effective policies and drive the e2e through them (KCL-98)`.

### Task 6: Cluster check (in the batch rebuild for KCL-94, 95, 71 and 98)

Not an SDD task; the controller runs it after rebuilding the cluster. On the cluster: attach a maintenance policy to a namespace and another to one table in it, and a discovery policy to the namespace; `GET /v1/tables/{uuid}/effective-policies` names the table's maintenance policy from `table`, the discovery policy from `namespace`, and a sibling table's maintenance policy from `namespace`; detach the table's maintenance attachment by its `pa-` id and the table falls back to the namespace's; `/mappings` and `applicable-policy` answer 404.
