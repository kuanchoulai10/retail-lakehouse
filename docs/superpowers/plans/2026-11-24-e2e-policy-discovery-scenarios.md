# Policy, Discovery and Table Information E2e Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the cluster verifications of discovery policies, effective policies, maintenance policies and the table information API into pytest e2e scenarios on the KCL-102 framework.

**Architecture:** Each scenario module owns a catalog of its own (`OwnedCatalog`, created through the platform API, storage under `s3://tm-e2e-catalogs/<catalog>`), so schedule, scan and "falls back to the default" checks hold without touching `iceberg`. New support code (own catalog, Temporal schedule and signal reads, a Kubernetes client for the worker restart) is unit-tested in `tests/e2e_support/`; the sweep learns owned catalogs' tables and restores revoked grants before dropping a catalog.

**Tech Stack:** pytest, httpx, PyIceberg, temporalio, pyarrow S3; Kubernetes API over httpx with the pod's ServiceAccount token.

**Spec:** Linear KCL-104 (description and completion conditions), read 2026-11-24. Inventory of every check, with its scenario or the reason it stays manual: `docs/superpowers/plans/2026-11-24-e2e-policy-discovery-inventory.md` (the "Final mapping" section at its end is binding where it differs from the inventory's proposal).

## Global Constraints

- Scenarios are black-box: no import of `base`, `bootstrap`, `context` (contracts `e2e-black-box`, `e2e-not-imported`); no Trino, no browser.
- Every name comes from `OwnedNames`; every create pushes its undo right after it succeeds; waits are `wait_until` with a bound.
- Never remove the platform's only role on a catalog: an unreadable catalog revokes only `CATALOG_MANAGE_CONTENT` and `CATALOG_MANAGE_METADATA` on `catalog_admin`, keeps `CATALOG_MANAGE_ACCESS`, and the cleanup (and the sweep, through `drop_catalog`) grants them back before the catalog is dropped.
- The default maintenance policy can be edited on a long-lived cluster: scenarios never edit it and assert its values only at `version == 1`.
- Where a plan's wording differs from the code, the code wins and the difference goes in the KCL-104 comment.
- One object per file; `from __future__ import annotations`; ABC over Protocol.

## Review Focus

- A scenario that revokes grants and then fails still leaves a catalog Polaris can empty and drop (grants restored first), including when the pod is cut short (the sweep).
- The worker restart leaves the platform with one ready worker and the scenario's schedule back, and the RBAC lets the e2e touch only the worker Deployment.
- A check that waits for "absent" (schedule deleted, catalog not scanned) cannot pass because the request failed or answered for another catalog.
- Scenarios run one after another in one session; none depends on another's state, and the `iceberg` catalog's scan state is not changed.
- `critical` stays within minutes: no `critical` scenario waits on discovery to manage a table or on a reconciliation.

## Rulings made while planning (the user delegated decisions)

- Ruling: markers by what a scenario waits on — `critical` = API answers only (discovery policies, effective policies, maintenance policies, removed routes); `full` = waits for discovery to manage a table, a reconciliation, Prometheus or a worker restart — cost if wrong: pre-merge catches fewer regressions.
- Ruling: one own catalog per module (`tm_e2e_catalog_<suffix>_<scenario>`), the catalog name pattern gains the scenario word — schedule and scanned-catalog checks are per catalog, and `iceberg` is shared — cost if wrong: a few seconds per module.
- Ruling: the worker restart uses a ServiceAccount `table-maintenance-e2e` with a Role allowing only `get` and `patch` on `deployments` named `table-maintenance-worker`; the scenario patches the pod template's `restartedAt` annotation (what `kubectl rollout restart` does) and waits on Temporal for the schedule — no `pods` access, no new library (httpx with the token and CA) — cost if wrong: an extra rule later.
- Ruling: 4.7 (Prometheus scaled to 0 gives a 502 trend) stays manual — it stops the shared table-metrics Prometheus and needs a Role in another namespace, and the 502 mapping is unit-tested — cost if wrong: the 502 path is only unit-tested.
- Ruling: 1.8 (`cannot_access` recorded) forces a rescan by updating the attached policy instead of waiting for the 600 s schedule; if the first cluster run shows only the scheduled scan records it, the check waits for the schedule — cost if wrong: up to 10 more minutes in `full`.

---

### Task 1: Shared support for own catalogs, Temporal reads, the Kubernetes client and the sweep

**Files:**
- Create: `e2e/support/load_iceberg.py`, `e2e/support/owned_catalog.py`, `e2e/support/schedule_exists.py`, `e2e/support/signals_received.py`, `e2e/support/kubernetes_api.py`
- Modify: `e2e/support/owned_names.py` (catalog takes a scenario), `e2e/support/drop_catalog.py` (grant back first), `e2e/support/sweep_leftovers.py` (owned catalogs' tables unmanaged before the drop), `e2e/conftest.py` (`iceberg` from `load_iceberg`), `e2e/test_catalog_round_trip.py` (scenario word), `e2e/support/__init__.py`
- Create: `platform/25-lakehouse-control-plane/e2e/rbac.yaml`; Modify: `e2e/pod.yaml` (`serviceAccountName`, token mounted), `e2e/run.sh` (apply `rbac.yaml` before the pod)
- Test: `tests/e2e_support/test_owned_names.py`, `test_drop_catalog.py`, `test_sweep_leftovers.py`, `test_schedule_exists.py`, `test_signals_received.py`, `test_kubernetes_api.py`

**Interfaces:**
- Produces: `OwnedNames.catalog(suffix, scenario) -> "tm_e2e_catalog_<suffix>_<scenario>"`; `load_iceberg(settings, warehouse) -> Catalog`; `OwnedCatalog.create(*, platform, polaris, s3, settings, cleanup, suffix, scenario) -> OwnedCatalog` with `.name`, `.iceberg`, `.revoke_reads(polaris)` (pushes nothing; the catalog's undo grants back), `.namespace(name, cleanup)` (creates through PyIceberg, pushes the drop); `schedule_exists(temporal, schedule_id) -> bool`; `signals_received(temporal, workflow_id) -> list[str]`; `KubernetesApi.from_service_account()`, `.restart_deployment(namespace, name) -> str` (returns the annotation value), `.deployment(namespace, name) -> dict`; `CONTENT_GRANTS = ("CATALOG_MANAGE_CONTENT", "CATALOG_MANAGE_METADATA")` in `drop_catalog.py`.

- [ ] Tests first for each new function and the changed sweep and drop order (drop_catalog: the two `PUT .../catalog-roles/catalog_admin/grants` come before any delete; sweep: an owned catalog's managed table is waited on before its maintenance policy and the catalog go). Watch them fail, implement, green.
- [ ] RBAC objects carry the Kubernetes label standard (`platform/CLAUDE.md`); `run.sh` applies them with `kubectl apply`; the pod sets `serviceAccountName: table-maintenance-e2e` and `automountServiceAccountToken: true`.
- [ ] `task gates:pre-pr` green; `run.sh critical` green on the cluster (the round trip under its new name); commit `feat(e2e): own catalogs, Temporal reads and a worker restart for scenarios (KCL-104)`.

### Task 2: Critical scenarios: discovery policies, maintenance policies, removed routes

**Files:** Create `e2e/test_discovery_policies.py` (1.1, 1.5, 1.6, 1.12), `e2e/test_maintenance_policies.py` (3.2, 3.3, 3.4), `e2e/test_removed_routes.py` (2.4, 2.8).

- [ ] Write each scenario from the inventory rows; run `run.sh critical`; a failure is either a scenario bug (fix it) or a code/plan difference (the code wins; note it for the issue comment).
- [ ] Green twice; commit `test(e2e): discovery and maintenance policy and removed route scenarios (KCL-104)`.

### Task 3: Critical scenario: effective policies

**Files:** Create `e2e/test_effective_policies.py` (2.1 by location, sibling, 2.2, 2.3, 2.5 404 half, 2.7).

- [ ] As Task 2; commit `test(e2e): effective policies scenario (KCL-104)`.

### Task 4: Full scenarios: discovery lifecycle and the unreadable catalog

**Files:** Create `e2e/test_discovery_lifecycle.py` (1.2, 1.3, 1.4, 6.2, 7.1), `e2e/test_discovery_unreadable_catalog.py` (1.7, 1.8, 2.5 403 half).

- [ ] The unreadable scenario reads `catalog_admin`'s grants before the revoke and asserts `CATALOG_MANAGE_ACCESS` is among them; its catalog's undo restores both grants first.
- [ ] Commit `test(e2e): discovery lifecycle and unreadable catalog scenarios (KCL-104)`.

### Task 5: Full scenarios: policy records and table information

**Files:** Create `e2e/test_policy_records.py` (3.5, 3.6, 3.8, 3.9, 6.4, 7.4), `e2e/test_table_information.py` (4.2, 5.2-5.6, 7.5, 7.6).

- [ ] Commit `test(e2e): policy record and table information scenarios (KCL-104)`.

### Task 6: Full scenarios: metric trends and the worker restart

**Files:** Create `e2e/test_metric_trends.py` (4.4), `e2e/test_worker_restart_schedules.py` (1.10).

- [ ] The restart scenario waits until the Deployment reports the new generation available, then polls `schedule_exists` (bound 240 s).
- [ ] Commit `test(e2e): metric trend and worker restart scenarios (KCL-104)`.

### Task 7: Docs, two runs, close

- [ ] Inventory: add the "Final mapping" section (each row → its module, or the reason it stays manual).
- [ ] Docs: wave 25 README e2e table (new scenarios, the ServiceAccount), backend `CLAUDE.md` (own catalogs), `project-history.md`.
- [ ] `task gates:nightly:e2e-full-test KUBE_CONTEXT=retail-lakehouse` twice, both pass; afterwards no e2e pod, no `tm_e2e_catalog_*` catalog, no `tm-e2e-*` policy, no `e2e_*` namespace, `catalog_admin` grants untouched on `iceberg`, one ready worker.
- [ ] Commit `docs(e2e): the policy and discovery scenarios (KCL-104)`; Linear comment (code/plan differences found), Done.
